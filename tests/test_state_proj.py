import pandas as pd
import pytest
from src.acquire.state_proj import parse_state_projections, check_guardrails


def _fixture(path):
    pd.DataFrame(
        {
            "Area": ["District of Columbia", "Maryland", "Virginia", "California"],
            "Occupation Code": ["15-1252", "15-1252", "15-1252", "15-1252"],
            "Percent Change": ["10.0", "12.5", "9.0", "20.0"],
        }
    ).to_csv(path, index=False)


def test_parse_pivots_to_state_columns(tmp_path):
    f = tmp_path / "state.csv"
    _fixture(f)
    df = parse_state_projections(f)
    assert set(df.columns) == {"soc", "dc_change_pct", "md_change_pct", "va_change_pct"}
    row = df[df["soc"] == "15-1252"].iloc[0]
    assert row["dc_change_pct"] == 10.0
    assert row["md_change_pct"] == 12.5
    assert row["va_change_pct"] == 9.0  # California excluded


def _bulk_fixture(path):
    # Mirror the Projections Central bulk CSV layout (SOC column named "code",
    # state under "areaname"), including a 00-0000 total row that must be dropped.
    pd.DataFrame(
        {
            "stfips": ["11", "24", "51", "06", "11"],
            "areaname": [
                "District of Columbia",
                "Maryland",
                "Virginia",
                "California",
                "District of Columbia",
            ],
            "code": ["15-1252", "15-1252", "15-1252", "15-1252", "00-0000"],
            "name": ["Software Developers"] * 4 + ["Total, All Occupations"],
            "baseyear": ["2022"] * 5,
            "projyear": ["2032"] * 5,
            "percentchange": ["19.6", "31.2", "21.4", "25.0", "3.1"],
        }
    ).to_csv(path, index=False)


def test_parse_bulk_csv_layout(tmp_path):
    f = tmp_path / "bulk.csv"
    _bulk_fixture(f)
    df = parse_state_projections(f)
    assert set(df["soc"]) == {
        "15-1252"
    }  # total row 00-0000 dropped, California excluded
    row = df[df["soc"] == "15-1252"].iloc[0]
    assert row["dc_change_pct"] == 19.6
    assert row["md_change_pct"] == 31.2
    assert row["va_change_pct"] == 21.4


def test_guardrails_pass_on_expected(tmp_path):
    raw = pd.DataFrame(
        {
            "stfips": ["11", "11", "24", "51"],
            "baseyear": ["2022"] * 4,
            "projyear": ["2032"] * 4,
        }
    )
    # Should not raise.
    check_guardrails(
        raw, expected={"11": 2, "24": 1, "51": 1}, vintage=("2022", "2032")
    )


def test_guardrails_hardfail_on_wrong_count():
    raw = pd.DataFrame(
        {
            "stfips": ["11", "24", "51"],
            "baseyear": ["2022"] * 3,
            "projyear": ["2032"] * 3,
        }
    )
    with pytest.raises(ValueError, match="row count"):
        check_guardrails(
            raw, expected={"11": 2, "24": 1, "51": 1}, vintage=("2022", "2032")
        )


def test_guardrails_hardfail_on_vintage_shift():
    raw = pd.DataFrame({"stfips": ["11"], "baseyear": ["2023"], "projyear": ["2033"]})
    with pytest.raises(ValueError, match="vintage"):
        check_guardrails(raw, expected={"11": 1}, vintage=("2022", "2032"))
