import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_cip, normalize_soc

log = logging.getLogger(__name__)
_NO_MATCH = {"no match", "no soc match", "none", ""}


def parse_crosswalk(xlsx_path) -> pd.DataFrame:
    raw = pd.read_excel(xlsx_path, header=None, dtype=str)
    header_idx = raw.index[raw.eq("CIP2020Code").any(axis=1)]
    if len(header_idx) == 0:
        raise ValueError(f"CIP2020Code header not found in {xlsx_path}")
    h = header_idx[0]
    df = raw.iloc[h + 1 :].copy()
    df.columns = raw.iloc[h].tolist()
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
    is_no_match = df["soc"].astype(str).str.strip().str.lower().isin(_NO_MATCH)
    df["soc"] = df["soc"].map(normalize_soc)
    df.loc[is_no_match, "soc"] = pd.NA
    df.loc[is_no_match, "soc_title"] = pd.NA
    return df.dropna(subset=["cip"]).reset_index(drop=True)


def get_crosswalk() -> pd.DataFrame:
    dest = config.RAW_DIR / "CIP2020_SOC2018_Crosswalk.xlsx"
    download(config.CROSSWALK_URL, dest)
    return parse_crosswalk(dest)
