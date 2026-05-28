import pandas as pd
from src.acquire.state_proj import parse_state_projections


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
