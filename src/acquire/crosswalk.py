import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_cip, normalize_soc

log = logging.getLogger(__name__)
_NO_MATCH = {"no match", "no soc match", "none", ""}


def parse_crosswalk(xlsx_path) -> pd.DataFrame:
    xl = pd.ExcelFile(xlsx_path)
    # The real NCES workbook keeps matched pairs in the 'CIP-SOC' sheet and CIPs with
    # no occupational match in 'Unmatched CIP Codes' (SOC 99-9999 / NO MATCH). Read
    # whichever CIP-first sheets exist, falling back to the first sheet otherwise.
    wanted = [s for s in ("CIP-SOC", "Unmatched CIP Codes") if s in xl.sheet_names]
    sheets = wanted if wanted else [xl.sheet_names[0]]

    frames = []
    for sh in sheets:
        raw = pd.read_excel(xlsx_path, sheet_name=sh, header=None, dtype=str)
        header_idx = raw.index[raw.eq("CIP2020Code").any(axis=1)]
        if len(header_idx) == 0:
            continue
        h = header_idx[0]
        block = raw.iloc[h + 1 :].copy()
        block.columns = raw.iloc[h].tolist()
        frames.append(block)
    if not frames:
        raise ValueError(f"CIP2020Code header not found in any sheet of {xlsx_path}")

    df = pd.concat(frames, ignore_index=True)
    df = df.rename(
        columns={
            "CIP2020Code": "cip",
            "CIP2020Title": "cip_title",
            "SOC2018Code": "soc",
            "SOC2018Title": "soc_title",
        }
    )[["cip", "cip_title", "soc", "soc_title"]]
    df = df.dropna(subset=["cip"])
    df["cip"] = df["cip"].map(normalize_cip)
    df["cip_title"] = df["cip_title"].astype(str).str.rstrip(".").str.strip()

    raw_soc = df["soc"].astype(str).str.strip()
    raw_title = df["soc_title"].astype(str).str.strip().str.lower()
    is_no_match = raw_soc.eq("99-9999") | raw_title.isin(_NO_MATCH)
    df["soc"] = df["soc"].map(normalize_soc)
    df.loc[is_no_match, "soc"] = pd.NA
    df.loc[is_no_match, "soc_title"] = pd.NA
    return df.dropna(subset=["cip"]).drop_duplicates().reset_index(drop=True)


def get_crosswalk() -> pd.DataFrame:
    dest = config.RAW_DIR / "CIP2020_SOC2018_Crosswalk.xlsx"
    download(config.CROSSWALK_URL, dest)
    return parse_crosswalk(dest)
