import datetime as dt
import logging

import pandas as pd
import requests

from src import config
from src.acquire.downloader import download
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


def check_guardrails(raw, expected=None, vintage=None):
    """Hard-fail (ValueError) if the upstream coverage or projection cycle has shifted.
    raw: the full multi-state DataFrame (string dtype) with stfips/baseyear/projyear columns."""
    expected = expected or config.STATE_EXPECTED_COUNTS
    vintage = vintage or config.STATE_PROJECTION_VINTAGE
    fips_col = _find(raw.columns, ["stfips", "fips"])
    base_col = _find(raw.columns, ["baseyear", "base year"])
    proj_col = _find(raw.columns, ["projyear", "proj year"])
    if not all([fips_col, base_col, proj_col]):
        raise ValueError(
            f"state projections guardrail: expected stfips/baseyear/projyear columns, got {list(raw.columns)}"
        )
    for fips, want in expected.items():
        got = int((raw[fips_col].astype(str).str.strip() == fips).sum())
        if got != want:
            raise ValueError(
                f"state projections guardrail: FIPS {fips} row count {got} != expected {want}. "
                "Upstream coverage changed; review before trusting (build hard-fails by design)."
            )
    sub = raw[raw[fips_col].astype(str).str.strip().isin(expected)]
    base_vals = set(sub[base_col].astype(str).str.strip().unique())
    proj_vals = set(sub[proj_col].astype(str).str.strip().unique())
    if base_vals != {vintage[0]} or proj_vals != {vintage[1]}:
        raise ValueError(
            f"state projections guardrail: vintage shifted (base={base_vals}, proj={proj_vals}); "
            f"expected {vintage}. Build hard-fails by design."
        )


def parse_state_projections(path) -> pd.DataFrame:
    raw = (
        pd.read_csv(path, dtype=str)
        if str(path).lower().endswith(".csv")
        else pd.read_excel(path, dtype=str)
    )
    area_col = _find(raw.columns, ["areaname", "area", "state"])
    # Projections Central's bulk CSV names the SOC column "code"; other files use "occupation code".
    soc_col = _find(raw.columns, ["occupation code", "soc", "code"])
    pct_col = _find(raw.columns, ["percent change", "percentchange", "percent"])
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
    raw = raw[raw["soc"] != "00-0000"]  # drop the all-occupations total row
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


def _resolve_csv_url() -> str:
    """Fetch the short-lived presigned CSV URL from the Projections Central file endpoint."""
    r = requests.get(
        config.STATE_PROJECTIONS_CSV_ENDPOINT,
        headers={"User-Agent": config.USER_AGENT},
        timeout=60,
    )
    r.raise_for_status()
    url = r.json().get("content")
    if not url:
        raise ValueError(
            f"Projections Central file endpoint returned no presigned URL: {r.text[:200]}"
        )
    return url


def get_state_projections() -> pd.DataFrame:
    """Download the Projections Central bulk long-term CSV (all states), archive it
    date-stamped, run hard-fail guardrails, and return the DC/MD/VA pivot.

    Network/availability failures raise requests exceptions (run.py degrades to empty
    columns). Guardrail failures raise ValueError and intentionally abort the build."""
    dated = config.RAW_DIR / f"projections_central_longterm_{dt.date.today()}.csv"
    if not dated.exists():
        download(_resolve_csv_url(), dated)
    raw = pd.read_csv(dated, dtype=str)
    check_guardrails(raw)
    return parse_state_projections(dated)
