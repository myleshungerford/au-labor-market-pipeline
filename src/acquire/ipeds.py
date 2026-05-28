import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_cip

log = logging.getLogger(__name__)


def parse_completions(csv_path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"CIPCODE": str}, low_memory=False)
    df.columns = [c.upper() for c in df.columns]
    df = df[
        (df["UNITID"] == config.AU_UNITID)
        & (df["AWLEVEL"] == config.BACHELORS_AWLEVEL)
        & (df["MAJORNUM"] == config.FIRST_MAJOR)
        & (df["CTOTALT"] > 0)
    ].copy()
    df = df[
        ~df["CIPCODE"].astype(str).str.startswith("99")
    ]  # CIP 99 is reserved for grand totals in CIP 2020
    df["cip"] = df["CIPCODE"].map(normalize_cip)
    df = df.dropna(subset=["cip"])
    out = (
        df.groupby("cip", as_index=False)["CTOTALT"]
        .sum()
        .rename(columns={"CTOTALT": "awards"})
    )
    return out.reset_index(drop=True)


def get_completions(force: bool = False) -> pd.DataFrame:
    dest = config.RAW_DIR / f"{config.IPEDS_COMPLETIONS_FILE}.zip"
    download(config.IPEDS_COMPLETIONS_URL, dest, force=force)
    with zipfile.ZipFile(dest) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"no CSV inside {dest.name}: {zf.namelist()}")
        # prefer the revised/final file if present
        name = sorted(names, key=lambda n: ("_rv" not in n.lower(), n))[0]
        log.info("reading %s from %s", name, dest.name)
        with zf.open(name) as fh:
            return parse_completions(io.BytesIO(fh.read()))
