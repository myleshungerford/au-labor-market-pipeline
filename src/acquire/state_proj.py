import logging
from pathlib import Path

import pandas as pd

from src import config
from src.codes import normalize_soc

log = logging.getLogger(__name__)

_STATE_ALIASES = {
    "DC": {"dc", "district of columbia"},
    "MD": {"md", "maryland"},
    "VA": {"va", "virginia"},
}


def _state_key(area: str):
    a = str(area).strip().lower()
    for key, names in _STATE_ALIASES.items():
        if a in names:
            return key
    return None


def _find(columns, needles):
    for col in columns:
        if any(n in str(col).lower() for n in needles):
            return col
    return None


def _to_num(value):
    s = str(value).strip().replace("%", "").replace(",", "")
    if s in {"", "nan", "-"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def parse_state_projections(path) -> pd.DataFrame:
    raw = (
        pd.read_csv(path, dtype=str)
        if str(path).lower().endswith(".csv")
        else pd.read_excel(path, dtype=str)
    )
    area_col = _find(raw.columns, ["area", "state"])
    soc_col = _find(raw.columns, ["occupation code", "soc"])
    pct_col = _find(raw.columns, ["percent change", "percent"])
    if not all([area_col, soc_col, pct_col]):
        raise ValueError(
            f"state projections missing columns; header was {list(raw.columns)}"
        )
    raw = raw.copy()
    raw["state"] = raw[area_col].map(_state_key)
    raw = raw.dropna(subset=["state"])
    raw["soc"] = raw[soc_col].map(normalize_soc)
    raw["pct"] = raw[pct_col].map(_to_num)
    raw = raw.dropna(subset=["soc"])
    wide = raw.pivot_table(index="soc", columns="state", values="pct", aggfunc="first")
    wide = wide.rename(
        columns={"DC": "dc_change_pct", "MD": "md_change_pct", "VA": "va_change_pct"}
    )
    for c in ("dc_change_pct", "md_change_pct", "va_change_pct"):
        if c not in wide.columns:
            wide[c] = pd.NA
    return wide.reset_index()[
        ["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]
    ]


def get_state_projections() -> pd.DataFrame:
    dest = config.RAW_DIR / "projections_central_longterm.csv"
    if not dest.exists():
        raise FileNotFoundError(
            f"Place the Projections Central 2022-32 long-term export at {dest} "
            f"(export from {config.STATE_PROJECTIONS_URL}). See spec Section 13."
        )
    return parse_state_projections(dest)
