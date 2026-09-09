"""Generate the ``window.PROGRAMS2`` records the briefs render from.

Reads the program one-pager workbook produced by the pipeline
(``au_program_onepager_data_<date>.xlsx``) and emits one record per program in the
exact shape the recovered ``op2-brief`` component consumes. The field derivations
here are pinned against the records already baked into the committed bundle
(see tests/test_brief_data.py), so any program the workbook covers is rendered
identically to the existing set.
"""

import math
from pathlib import Path

import pandas as pd

from src.codes import normalize_cip

DATA_SHEET = "Program One-Pager Data"
OCC_SHEET = "Program Occupations"


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _num(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)


def _count(value):
    number = _num(value)
    return None if number is None else int(round(number))


def _flag(value) -> bool:
    # bool(nan) is True in Python, so a missing flag must be coerced to False first.
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    return bool(value)


def _breadth(displayed_count: int, has_match: bool) -> str:
    if not has_match or displayed_count == 0:
        return "No standard mapping"
    if displayed_count <= 3:
        return "Focused"
    if displayed_count <= 7:
        return "Moderate"
    return "Broad"


def _occupations(occ_rows: pd.DataFrame) -> list[dict]:
    # A CIP with no crosswalk match still gets one placeholder row (empty SOC); it is
    # not a real occupation and must not appear or count toward the displayed total.
    real = occ_rows[occ_rows["soc"].map(_text) != ""]
    ranked = real.sort_values("nat_tot_emp", ascending=False, kind="stable")
    displayed = ranked[~ranked["do_not_display_on_one_pager"].astype(bool)]
    return [
        {
            "soc": _text(row["soc"]),
            "title": _text(row["soc_title"]),
            "catchall": _flag(row["catch_all"]),
            "hide": _flag(row["do_not_display_on_one_pager"]),
            "note": _text(row["one_pager_display_note"]),
            "natEmp": _count(row["nat_tot_emp"]),
            "natMed": _count(row["nat_median"]),
            "natGrowth": _num(row["nat_growth_pct"]),
            "natOpen": _count(row["nat_annual_openings"]),
            "metroMed": _count(row["metro_median"]),
            "metroSuppressed": _flag(row["metro_suppressed"]),
            "laborCipTitle": _text(row["labor_cip_title"]),
            "eduEntry": _text(row["entry_education"]),
        }
        for _, row in displayed.iterrows()
    ]


def _record(row: pd.Series, occ_rows: pd.DataFrame) -> dict:
    occs = _occupations(occ_rows)
    displayed_count = len(occs)
    match = _flag(row["soc_match"])
    labor_cip_title = occs[0]["laborCipTitle"] if occs else ""
    single_teaching = displayed_count == 1 and occs[0]["soc"].startswith("25-")
    return {
        "id": _text(row["program_id"]),
        "name": _text(row["program_name"]),
        "school": _text(row["school_college"]),
        "cip": normalize_cip(row["cip"]),
        "cipTitle": _text(row["cip_title"]),
        "laborCip": normalize_cip(row["labor_market_cip"]),
        "match": match,
        "occCount": _count(row["occupation_count"]),
        "displayedCount": displayed_count,
        "breadth": _breadth(displayed_count, match),
        "catchall": _flag(row["catch_all_present"]),
        "metroPartial": _flag(row["metro_data_partial"]),
        "isProxy": _text(row["labor_market_data_level"]) == "CIP (proxy)",
        "ready": _flag(row["one_pager_ready"]),
        "proxyNote": _text(row["labor_market_proxy_note"]),
        "proxyCipTitle": labor_cip_title,
        "blocker": _text(row["one_pager_blocker"]),
        "natWage": _num(row["wtd_median_wage_national"]),
        "natWageExcl": _num(row["wtd_median_wage_national_excl_catchall"]),
        "entryWage": _num(row["wtd_median_wage_bachelors_entry"]),
        "metroWage": _num(row["wtd_metro_median_wage"]),
        "growth": _num(row["wtd_growth_pct_national"]),
        "openings": _count(row["total_annual_openings"]),
        "openingsExcl": _count(row["total_annual_openings_excl_catchall"]),
        "singleTeaching": single_teaching,
        "occs": occs,
    }


def build_programs2(workbook_path: Path) -> list[dict]:
    """Return one ``PROGRAMS2`` record per program in the one-pager workbook."""
    data = pd.read_excel(workbook_path, sheet_name=DATA_SHEET)
    occ = pd.read_excel(workbook_path, sheet_name=OCC_SHEET)
    records = []
    for _, row in data.iterrows():
        occ_rows = occ[occ["program_id"] == row["program_id"]]
        records.append(_record(row, occ_rows))
    return records
