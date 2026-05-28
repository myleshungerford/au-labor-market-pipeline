import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_soc

log = logging.getLogger(__name__)

_PROJ_SHEET = "Table 1.2"  # "Occupational projections ... and worker characteristics"
# BLS Table 1.2 reports employment and openings in THOUSANDS; convert these to actual counts.
_COUNT_COLS = ("emp_base", "emp_proj", "change_num", "annual_openings")

# canonical -> list of substrings to match (case-insensitive) in the real header
_COLMAP = {
    "soc": ["matrix code", "soc code", "occupation code"],
    "occ_type": ["occupation type"],
    "emp_base": ["employment, 2024", "employment 2024"],
    "emp_proj": ["employment, 2034", "employment 2034"],
    "change_num": ["change, numeric", "numeric change"],
    "change_pct": ["change, percent", "percent change"],
    "annual_openings": ["openings"],
    "median_wage": ["median annual wage", "median wage"],
    "entry_education": [
        "education needed for entry",
        "entry-level education",
        "entry level education",
    ],
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
    # The real BLS workbook puts the data on sheet "Table 1.2" with a title row
    # above the column header; simple single-sheet inputs are read as-is.
    xl = pd.ExcelFile(path)
    if _PROJ_SHEET in xl.sheet_names:
        raw = pd.read_excel(path, sheet_name=_PROJ_SHEET, header=1, dtype=str)
    else:
        raw = pd.read_excel(path, dtype=str)
    resolved = {
        canon: _find(raw.columns, needles) for canon, needles in _COLMAP.items()
    }
    required = [k for k in _COLMAP if k != "occ_type"]  # occ_type is optional
    missing = [k for k in required if resolved[k] is None]
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
    if resolved["occ_type"] is not None:
        out["_occ_type"] = raw[resolved["occ_type"]].astype(str).str.strip().str.lower()

    out = out.dropna(subset=["soc"])
    if "_occ_type" in out.columns:
        # "Line item" rows are detailed occupations; "Summary" rows are aggregates.
        out = out[out["_occ_type"] == "line item"].drop(columns="_occ_type")
    else:
        out = out[
            out["soc"].str.match(r"^\d{2}-\d{4}$") & ~out["soc"].str.endswith("0000")
        ]

    # Convert thousands -> actual counts so downstream openings read as real jobs.
    for col in _COUNT_COLS:
        out[col] = [v * 1000 if pd.notna(v) else pd.NA for v in out[col]]
    return out.drop_duplicates(subset=["soc"]).reset_index(drop=True)


def get_projections(force: bool = False) -> pd.DataFrame:
    dest = config.RAW_DIR / "ep_occupation_2024_34.xlsx"
    download(config.PROJECTIONS_URL, dest, force=force)
    return parse_projections(dest)
