import logging

import pandas as pd

from src import config

log = logging.getLogger(__name__)


def _is_catch_all(soc, soc_title) -> bool:
    if soc in config.CATCH_ALL_SOCS:
        return True
    return str(soc_title).strip().lower().endswith("all other")


def _one_pager_display_note(soc, soc_title):
    title = str(soc_title).strip()
    if pd.isna(soc):
        return pd.NA
    if soc == "11-1021":
        return "general management category"
    if title.lower().endswith("all other"):
        return "residual catch-all occupation"
    if soc in config.CATCH_ALL_SOCS:
        return "broad catch-all occupation"
    return pd.NA


def build_detail(mapping, oews_nat, oews_metro, proj, state) -> pd.DataFrame:
    d = mapping.copy()

    nat = oews_nat.rename(columns={"tot_emp": "nat_tot_emp", "a_median": "nat_median"})
    d = d.merge(nat[["soc", "nat_tot_emp", "nat_median"]], on="soc", how="left")

    p = proj.rename(
        columns={
            "change_pct": "nat_growth_pct",
            "annual_openings": "nat_annual_openings",
        }
    )
    d = d.merge(
        p[["soc", "nat_growth_pct", "nat_annual_openings", "entry_education"]],
        on="soc",
        how="left",
    )

    m = oews_metro.rename(
        columns={"tot_emp": "metro_tot_emp", "a_median": "metro_median"}
    )
    d = d.merge(
        m[["soc", "metro_tot_emp", "metro_median", "loc_quotient", "metro_suppressed"]],
        on="soc",
        how="left",
    )

    d = d.merge(
        state[["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]],
        on="soc",
        how="left",
    )

    d["catch_all"] = [
        _is_catch_all(s, t) if pd.notna(s) else False
        for s, t in zip(d["soc"], d["soc_title"])
    ]
    d["one_pager_display_note"] = [
        _one_pager_display_note(s, t) for s, t in zip(d["soc"], d["soc_title"])
    ]
    # Hide catch-all occupations from the one-pager list, but only for CIPs that already
    # carry enough non-catch-all matched occupations. Data-poor CIPs keep their catch-all
    # so the one-pager is not left blank (see config.ONE_PAGER_MIN_REAL_OCCUPATIONS).
    real_occ_per_cip = (
        d[(d["soc_match"] == True) & (~d["catch_all"])]  # noqa: E712
        .groupby("cip")["soc"]
        .nunique()
    )
    cip_real_occ = d["cip"].map(real_occ_per_cip).fillna(0)
    d["do_not_display_on_one_pager"] = d["catch_all"] & (
        cip_real_occ >= config.ONE_PAGER_MIN_REAL_OCCUPATIONS
    )
    d["entry_education"] = d["entry_education"].where(
        d["entry_education"].notna(), pd.NA
    )

    cols = [
        "cip",
        "program_name",
        "program_short_name",
        "cip_title",
        "program_name_note",
        "awards",
        "cip_in_ipeds_completions",
        "awards_source_note",
        "soc",
        "soc_title",
        "soc_match",
        "catch_all",
        "do_not_display_on_one_pager",
        "one_pager_display_note",
        "entry_education",
        "nat_tot_emp",
        "nat_median",
        "nat_growth_pct",
        "nat_annual_openings",
        "metro_tot_emp",
        "metro_median",
        "loc_quotient",
        "metro_suppressed",
        "dc_change_pct",
        "md_change_pct",
        "va_change_pct",
    ]
    for c in cols:
        if c not in d.columns:
            d[c] = pd.NA
    return d[cols].reset_index(drop=True)
