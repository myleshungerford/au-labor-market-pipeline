import pandas as pd
from src.transform.join import build_detail, _is_catch_all


def test_is_catch_all_rule():
    assert (
        _is_catch_all("11-1021", "General and Operations Managers") is True
    )  # config list
    assert (
        _is_catch_all("13-1199", "Business Specialists, All Other") is True
    )  # title rule
    assert _is_catch_all("15-1252", "Software Developers") is False


def test_build_detail_attaches_metrics_and_flags():
    mapping = pd.DataFrame(
        {
            "cip": ["11.0701", "30.9999"],
            "program_name": ["CS", "Multi"],
            "awards": [42, 7],
            "soc": ["15-1252", pd.NA],
            "soc_title": ["Software Developers", pd.NA],
            "soc_match": [True, False],
        }
    )
    nat = pd.DataFrame(
        {
            "soc": ["15-1252"],
            "tot_emp": [1500000.0],
            "a_median": [120000.0],
            "a_mean": [130000.0],
            "a_pct10": [70000.0],
            "a_pct25": [95000.0],
            "a_pct75": [150000.0],
            "a_pct90": [190000.0],
            "national_suppressed": [False],
        }
    )
    metro = pd.DataFrame(
        {
            "soc": ["15-1252"],
            "tot_emp": [60000.0],
            "a_median": [135000.0],
            "a_mean": [140000.0],
            "a_pct10": [80000.0],
            "a_pct25": [105000.0],
            "a_pct75": [160000.0],
            "a_pct90": [200000.0],
            "loc_quotient": [1.8],
            "metro_suppressed": [False],
        }
    )
    proj = pd.DataFrame(
        {
            "soc": ["15-1252"],
            "emp_base": [1500.0],
            "emp_proj": [1700.0],
            "change_num": [200.0],
            "change_pct": [13.3],
            "annual_openings": [150.0],
            "median_wage": [120000.0],
            "entry_education": ["Bachelor's degree"],
        }
    )
    state = pd.DataFrame(
        {
            "soc": ["15-1252"],
            "dc_change_pct": [10.0],
            "md_change_pct": [12.5],
            "va_change_pct": [9.0],
        }
    )

    d = build_detail(mapping, nat, metro, proj, state)
    cs = d[d["cip"] == "11.0701"].iloc[0]
    assert cs["nat_median"] == 120000.0
    assert cs["nat_growth_pct"] == 13.3
    assert cs["nat_annual_openings"] == 150.0
    assert cs["metro_median"] == 135000.0
    assert cs["loc_quotient"] == 1.8
    assert cs["entry_education"] == "Bachelor's degree"
    assert cs["catch_all"] == False
    nm = d[d["cip"] == "30.9999"].iloc[0]
    assert pd.isna(nm["nat_median"])
    assert nm["soc_match"] == False
