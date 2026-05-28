import pandas as pd
from src.acquire.projections import parse_projections


def _fixture(path):
    pd.DataFrame(
        {
            "2023 National Employment Matrix code": ["15-1252", "19-3094", "15-0000"],
            "2023 National Employment Matrix title": [
                "Software Developers",
                "Political Scientists",
                "Computer Occupations",
            ],
            "Employment, 2024": ["1500.0", "6.0", "5000.0"],
            "Employment, 2034": ["1700.0", "6.3", "5200.0"],
            "Employment change, numeric, 2024-34": ["200.0", "0.3", "200.0"],
            "Employment change, percent, 2024-34": ["13.3", "5.0", "4.0"],
            "Occupational openings, 2024-34 annual average": ["150.0", "0.6", "400.0"],
            "Median annual wage, 2024(1)": ["120000", "130000", "100000"],
            "Typical entry-level education": [
                "Bachelor's degree",
                "Master's degree",
                "Bachelor's degree",
            ],
        }
    ).to_excel(path, index=False)


def test_parse_maps_columns_and_drops_aggregates(tmp_path):
    f = tmp_path / "proj.xlsx"
    _fixture(f)
    df = parse_projections(f)
    assert set(df.columns) == {
        "soc",
        "emp_base",
        "emp_proj",
        "change_num",
        "change_pct",
        "annual_openings",
        "median_wage",
        "entry_education",
    }
    assert set(df["soc"]) == {"15-1252", "19-3094"}  # 15-0000 aggregate dropped
    cs = df[df["soc"] == "15-1252"].iloc[0]
    assert cs["change_pct"] == 13.3
    assert cs["annual_openings"] == 150.0
    assert cs["entry_education"] == "Bachelor's degree"
