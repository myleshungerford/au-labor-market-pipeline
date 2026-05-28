import logging
import zipfile
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_soc

log = logging.getLogger(__name__)

_GROUP_NAMES = ("O_GROUP", "OCC_GROUP")
_LQ_NAMES = ("LOC_QUOTIENT", "LOC Q", "LOC_Q")
_PCTS = {
    "a_pct10": "A_PCT10",
    "a_pct25": "A_PCT25",
    "a_pct75": "A_PCT75",
    "a_pct90": "A_PCT90",
}


def _to_num(value):
    if value is None:
        return pd.NA
    s = str(value).strip().replace(",", "")
    if s == "" or s in {"*", "**", "#", "##"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def _resolve_group_col(columns) -> str:
    for name in _GROUP_NAMES:
        if name in columns:
            return name
    raise ValueError(f"no OEWS group column ({_GROUP_NAMES}) in {list(columns)}")


def _resolve_lq_col(columns):
    for name in _LQ_NAMES:
        if name in columns:
            return name
    return None


def parse_oews(xlsx_path, *, is_metro: bool) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]
    group_col = _resolve_group_col(df.columns)
    required = ["AREA", "OCC_CODE", "TOT_EMP", "A_MEAN", "A_MEDIAN", *_PCTS.values()]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"OEWS file missing columns {missing}; header was {list(df.columns)}"
        )

    df = df[df[group_col].astype(str).str.lower() == "detailed"].copy()
    if is_metro:
        df = df[df["AREA"].astype(str).str.strip() == config.DC_MSA_CODE].copy()

    out = pd.DataFrame()
    out["soc"] = df["OCC_CODE"].map(normalize_soc)
    out["tot_emp"] = df["TOT_EMP"].map(_to_num)
    out["a_median"] = df["A_MEDIAN"].map(_to_num)
    out["a_mean"] = df["A_MEAN"].map(_to_num)
    for dst, src in _PCTS.items():
        out[dst] = df[src].map(_to_num)

    flag = "metro_suppressed" if is_metro else "national_suppressed"
    out[flag] = out["a_median"].isna()
    if is_metro:
        lq = _resolve_lq_col(df.columns)
        out["loc_quotient"] = df[lq].map(_to_num) if lq else pd.NA
    return (
        out.dropna(subset=["soc"])
        .drop_duplicates(subset=["soc"])
        .reset_index(drop=True)
    )


def _extract_member(zip_path, *, prefer: str) -> Path:
    """Extract the OEWS data spreadsheet whose member name contains `prefer`
    (case-insensitive), skipping the field/file descriptions workbook. The metro
    zip bundles several files (BOS = balance-of-state/nonmetro, MSA = metro areas,
    file_descriptions), so the right one must be chosen explicitly, not taken first."""
    with zipfile.ZipFile(zip_path) as zf:
        sheets = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
        data = [n for n in sheets if "description" not in n.lower()]
        if not data:
            raise ValueError(f"no data spreadsheet in {zip_path}: {zf.namelist()}")
        chosen = next((n for n in data if prefer.lower() in Path(n).name.lower()), None)
        if chosen is None:
            if len(data) == 1:
                chosen = data[0]
            else:
                raise ValueError(
                    f"no OEWS member matching {prefer!r} in {zip_path}; candidates: {data}"
                )
        target = config.RAW_DIR / Path(chosen).name
        with zf.open(chosen) as fh, open(target, "wb") as out:
            out.write(fh.read())
    return target


def get_oews_national(force: bool = False) -> pd.DataFrame:
    z = config.RAW_DIR / config.OEWS_NATIONAL_ZIP
    download(config.OEWS_NATIONAL_URL, z, force=force)
    # "national" (not "nat") so we never match the 4-digit aggregate file nat4d_*.
    return parse_oews(_extract_member(z, prefer="national"), is_metro=False)


def get_oews_metro(force: bool = False) -> pd.DataFrame:
    z = config.RAW_DIR / config.OEWS_METRO_ZIP
    download(config.OEWS_METRO_URL, z, force=force)
    return parse_oews(_extract_member(z, prefer="MSA"), is_metro=True)
