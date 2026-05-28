import logging

import pandas as pd

from src import config

log = logging.getLogger(__name__)


def employment_weighted_mean(values, weights):
    total_w = 0.0
    acc = 0.0
    for v, w in zip(values, weights):
        if v is None or w is None or pd.isna(v) or pd.isna(w):
            continue
        acc += float(v) * float(w)
        total_w += float(w)
    return acc / total_w if total_w > 0 else pd.NA


def _summarize_group(g: pd.DataFrame) -> pd.Series:
    matched = g[g["soc_match"] == True]  # noqa: E712
    excl = matched[matched["catch_all"] == False]  # noqa: E712
    bach = matched[matched["entry_education"].isin(config.BACHELORS_PLUS_EDUCATION)]
    return pd.Series(
        {
            "program_name": g["program_name"].iloc[0],
            "awards": int(g["awards"].iloc[0]),
            "occupation_count": int(matched["soc"].nunique()),
            "soc_match": bool(matched.shape[0] > 0),
            "catch_all_present": bool((matched["catch_all"] == True).any()),  # noqa: E712
            "metro_data_partial": bool(
                matched["metro_suppressed"].isna().any()
                or (matched["metro_suppressed"] == True).any()
            )
            if matched.shape[0]
            else False,  # noqa: E712
            "wtd_median_wage_national": employment_weighted_mean(
                matched["nat_median"], matched["nat_tot_emp"]
            ),
            "wtd_median_wage_national_excl_catchall": employment_weighted_mean(
                excl["nat_median"], excl["nat_tot_emp"]
            ),
            "wtd_median_wage_bachelors_entry": employment_weighted_mean(
                bach["nat_median"], bach["nat_tot_emp"]
            ),
            "occ_median_min": matched["nat_median"].min(),
            "occ_median_max": matched["nat_median"].max(),
            "wtd_growth_pct_national": employment_weighted_mean(
                matched["nat_growth_pct"], matched["nat_tot_emp"]
            ),
            "total_annual_openings": matched["nat_annual_openings"].sum(min_count=1),
            "wtd_metro_median_wage": employment_weighted_mean(
                matched["metro_median"], matched["metro_tot_emp"]
            ),
        }
    )


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    # pandas 3.0 excludes the grouping column from the applied frame by default
    # and removed the include_groups kwarg, so do not pass it.
    summary = detail.groupby("cip", sort=True).apply(_summarize_group).reset_index()
    ordered = [
        "cip",
        "program_name",
        "awards",
        "occupation_count",
        "soc_match",
        "catch_all_present",
        "metro_data_partial",
        "wtd_median_wage_national",
        "wtd_median_wage_national_excl_catchall",
        "wtd_median_wage_bachelors_entry",
        "occ_median_min",
        "occ_median_max",
        "wtd_growth_pct_national",
        "total_annual_openings",
        "wtd_metro_median_wage",
    ]
    return summary[ordered]
