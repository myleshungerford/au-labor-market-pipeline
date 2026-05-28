import math
import pandas as pd
import pytest
from src.transform.aggregate import employment_weighted_mean, build_summary


def test_weighted_mean_basic():
    assert employment_weighted_mean([100.0, 200.0], [1.0, 3.0]) == 175.0


def test_weighted_mean_skips_na_pairs():
    assert employment_weighted_mean([100.0, None, 200.0], [1.0, 5.0, 3.0]) == 175.0


def test_weighted_mean_all_na_returns_na():
    assert pd.isna(employment_weighted_mean([None, None], [1.0, 2.0]))
    assert pd.isna(employment_weighted_mean([], []))


def _detail():
    return pd.DataFrame(
        {
            "cip": ["11.0701", "11.0701", "30.9999"],
            "program_name": ["CS", "CS", "Multi"],
            "awards": [42, 42, 7],
            "soc": ["15-1252", "11-1021", pd.NA],
            "soc_title": [
                "Software Developers",
                "General and Operations Managers",
                pd.NA,
            ],
            "soc_match": [True, True, False],
            "catch_all": [False, True, False],
            "entry_education": ["Bachelor's degree", "Bachelor's degree", pd.NA],
            "nat_tot_emp": [1000.0, 3000.0, pd.NA],
            "nat_median": [120000.0, 100000.0, pd.NA],
            "nat_growth_pct": [13.0, 5.0, pd.NA],
            "nat_annual_openings": [150.0, 400.0, pd.NA],
            "metro_tot_emp": [600.0, 1400.0, pd.NA],
            "metro_median": [135000.0, 110000.0, pd.NA],
            "loc_quotient": [1.8, 1.2, pd.NA],
            "metro_suppressed": [False, False, pd.NA],
            "dc_change_pct": [10.0, 4.0, pd.NA],
            "md_change_pct": [12.0, 5.0, pd.NA],
            "va_change_pct": [9.0, 4.0, pd.NA],
        }
    )


def test_summary_weighted_and_flags():
    s = build_summary(_detail())
    cs = s[s["cip"] == "11.0701"].iloc[0]
    # all-occupation weighted wage: (120000*1000 + 100000*3000)/4000 = 105000
    assert cs["wtd_median_wage_national"] == 105000.0
    # excluding catch-all (drop 11-1021): only 15-1252 -> 120000
    assert cs["wtd_median_wage_national_excl_catchall"] == 120000.0
    # bachelor's-entry: both are bachelor's -> same as all = 105000
    assert cs["wtd_median_wage_bachelors_entry"] == 105000.0
    assert cs["occupation_count"] == 2
    assert cs["occ_median_min"] == 100000.0
    assert cs["occ_median_max"] == 120000.0
    assert cs["total_annual_openings"] == 550.0
    assert cs["catch_all_present"] == True
    assert cs["soc_match"] == True
    # metro weighted wage: (135000*600 + 110000*1400)/2000 = 117500
    assert cs["wtd_metro_median_wage"] == 117500.0

    nm = s[s["cip"] == "30.9999"].iloc[0]
    assert nm["soc_match"] == False
    assert nm["occupation_count"] == 0
    assert pd.isna(nm["wtd_median_wage_national"])
