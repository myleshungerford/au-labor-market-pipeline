import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_soc

log = logging.getLogger(__name__)

# canonical -> list of substrings to match (case-insensitive) in the real header
_COLMAP = {
    "soc": ["matrix code", "soc code", "occupation code"],
    "emp_base": ["employment, 2024", "employment 2024"],
    "emp_proj": ["employment, 2034", "employment 2034"],
    "change_num": ["change, numeric", "numeric change"],
    "change_pct": ["change, percent", "percent change"],
    "annual_openings": ["openings"],
    "median_wage": ["median annual wage", "median wage"],
    "entry_education": ["entry-level education", "entry level education"],
}


def _find(columns, needles):
    for col in columns:
        low = str(col).lower()
        if any(n in low for n in needles):
            return col
    return None


def _to_num(value):
    s = str(value).strip().replace(",", "").replace("$", "")
    if s in {"", "nan", "-"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def parse_projections(path) -> pd.DataFrame:
    raw = pd.read_excel(path, dtype=str)
    resolved = {
        canon: _find(raw.columns, needles) for canon, needles in _COLMAP.items()
    }
    missing = [k for k, v in resolved.items() if v is None]
    if missing:
        raise ValueError(
            f"projections file missing columns {missing}; header was {list(raw.columns)}"
        )
    out = pd.DataFrame()
    out["soc"] = raw[resolved["soc"]].map(normalize_soc)
    for num_col in (
        "emp_base",
        "emp_proj",
        "change_num",
        "change_pct",
        "annual_openings",
        "median_wage",
    ):
        out[num_col] = raw[resolved[num_col]].map(_to_num)
    out["entry_education"] = raw[resolved["entry_education"]].astype(str).str.strip()
    out = out.dropna(subset=["soc"])
    out = out[out["soc"].str.match(r"^\d{2}-\d{4}$") & ~out["soc"].str.endswith("0000")]
    return out.drop_duplicates(subset=["soc"]).reset_index(drop=True)


def get_projections() -> pd.DataFrame:
    # PROJECTIONS_URL is a landing page; resolve the .xlsx link at runtime then cache it.
    dest = config.RAW_DIR / "ep_occupation_2024_34.xlsx"
    if not dest.exists():
        raise FileNotFoundError(
            f"Place the BLS EP 2024-34 occupational data xlsx at {dest} "
            f"(resolve the download link from {config.PROJECTIONS_URL}). "
            "See spec Section 13."
        )
    return parse_projections(dest)
