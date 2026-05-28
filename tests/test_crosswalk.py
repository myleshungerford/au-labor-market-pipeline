import pandas as pd
from src.acquire.crosswalk import parse_crosswalk


def _make_fixture(path):
    # Two header padding rows above the real header, like the real file.
    rows = [
        ["Crosswalk title", None, None, None],
        [None, None, None, None],
        ["CIP2020Code", "CIP2020Title", "SOC2018Code", "SOC2018Title"],
        ["11.0701", "Computer Science.", "15-1252", "Software Developers"],
        ["11.0701", "Computer Science.", "15-1211", "Computer Systems Analysts"],
        ["45.1001", "Political Science.", "19-3094", "Political Scientists"],
        ["30.9999", "Other Multi/Interdisc.", "No Match", "No Match"],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_parse_expands_and_normalizes(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    assert set(df.columns) == {"cip", "cip_title", "soc", "soc_title"}
    cs = df[df["cip"] == "11.0701"]
    assert sorted(cs["soc"]) == ["15-1211", "15-1252"]


def test_no_match_rows_have_na_soc(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    pol = df[df["cip"] == "30.9999"]
    assert len(pol) == 1
    assert pd.isna(pol.iloc[0]["soc"])
