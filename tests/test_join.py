import pandas as pd
from src.transform.join import build_detail, _is_catch_all, _one_pager_display_note


def test_is_catch_all_rule():
    assert (
        _is_catch_all("11-1021", "General and Operations Managers") is True
    )  # config list
    assert (
        _is_catch_all("13-1199", "Business Specialists, All Other") is True
    )  # title rule
    assert _is_catch_all("15-1252", "Software Developers") is False


def test_one_pager_display_note_flags_broad_categories():
    assert (
        _one_pager_display_note("11-1021", "General and Operations Managers")
        == "general management category"
    )
    assert (
        _one_pager_display_note("11-9199", "Managers, All Other")
        == "residual catch-all occupation"
    )
    assert pd.isna(_one_pager_display_note("15-1252", "Software Developers"))


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
    assert cs["do_not_display_on_one_pager"] == False
    assert pd.isna(cs["one_pager_display_note"])
    nm = d[d["cip"] == "30.9999"].iloc[0]
    assert pd.isna(nm["nat_median"])
    assert nm["soc_match"] == False
    assert nm["do_not_display_on_one_pager"] == False


def _empty_wage_frames():
    empty = pd.DataFrame({"soc": []})
    return (
        empty.assign(tot_emp=[], a_median=[]),
        empty.assign(tot_emp=[], a_median=[], loc_quotient=[], metro_suppressed=[]),
        empty.assign(change_pct=[], annual_openings=[], entry_education=[]),
        empty.assign(dc_change_pct=[], md_change_pct=[], va_change_pct=[]),
    )


def test_catch_all_flagged_and_noted_regardless_of_display():
    # The catch_all flag and the display note are intrinsic to the occupation and do not
    # depend on how many other occupations the CIP has.
    mapping = pd.DataFrame(
        {
            "cip": ["45.0901", "52.0201"],
            "program_name": ["IR", "Business"],
            "awards": [386, 239],
            "soc": ["11-9199", "11-1021"],
            "soc_title": ["Managers, All Other", "General and Operations Managers"],
            "soc_match": [True, True],
        }
    )
    detail = build_detail(mapping, *_empty_wage_frames())
    ir = detail[detail["cip"] == "45.0901"].iloc[0]
    assert ir["catch_all"] == True
    assert ir["one_pager_display_note"] == "residual catch-all occupation"
    business = detail[detail["cip"] == "52.0201"].iloc[0]
    assert business["catch_all"] == True
    assert business["one_pager_display_note"] == "general management category"


def test_catch_all_hidden_only_when_cip_has_enough_real_occupations():
    # CIP A: 5 non-catch-all + 1 catch-all -> catch-all hidden from the one-pager.
    # CIP B: 1 non-catch-all + 1 catch-all -> catch-all surfaced (data-poor rescue).
    mapping = pd.DataFrame(
        {
            "cip": ["10.0001"] * 6 + ["10.0002"] * 2,
            "program_name": ["A"] * 6 + ["B"] * 2,
            "awards": [0] * 8,
            "soc": [
                "15-0001",
                "15-0002",
                "15-0003",
                "15-0004",
                "15-0005",
                "11-9199",
                "15-0006",
                "11-9199",
            ],
            "soc_title": [
                "Dev1",
                "Dev2",
                "Dev3",
                "Dev4",
                "Dev5",
                "Managers, All Other",
                "Dev6",
                "Managers, All Other",
            ],
            "soc_match": [True] * 8,
        }
    )
    detail = build_detail(mapping, *_empty_wage_frames())

    a_catch = detail[(detail["cip"] == "10.0001") & (detail["soc"] == "11-9199")].iloc[
        0
    ]
    assert a_catch["catch_all"] == True
    assert a_catch["do_not_display_on_one_pager"] == True  # >=5 real occ -> hide

    b_catch = detail[(detail["cip"] == "10.0002") & (detail["soc"] == "11-9199")].iloc[
        0
    ]
    assert b_catch["catch_all"] == True
    assert b_catch["do_not_display_on_one_pager"] == False  # <5 real occ -> surface

    a_real = detail[(detail["cip"] == "10.0001") & (detail["soc"] == "15-0001")].iloc[0]
    assert a_real["do_not_display_on_one_pager"] == False  # real occ never hidden
