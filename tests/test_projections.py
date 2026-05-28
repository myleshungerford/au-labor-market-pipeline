import pandas as pd
from src.acquire.projections import parse_projections


def _fixture(path):
    # Mirror the real BLS workbook: data on sheet "Table 1.2" with a title row above
    # the header, an "Occupation type" column (Line item = detailed, Summary = aggregate),
    # and employment/openings reported in thousands.
    df = pd.DataFrame(
        {
            "2024 National Employment Matrix title": [
                "Total, all occupations",
                "Software Developers",
                "Political Scientists",
                "Computer Occupations",
            ],
            "2024 National Employment Matrix code": [
                "00-0000",
                "15-1252",
                "19-3094",
                "15-1200",
            ],
            "Occupation type": ["Summary", "Line item", "Line item", "Summary"],
            "Employment, 2024": ["169956.1", "1500.0", "6.0", "5000.0"],
            "Employment, 2034": ["175167.9", "1700.0", "6.3", "5200.0"],
            "Employment change, numeric, 2024-34": ["5211.8", "200.0", "0.3", "200.0"],
            "Employment change, percent, 2024-34": ["3.1", "13.3", "5.0", "4.0"],
            "Occupational openings, 2024-34 annual average": [
                "18863.3",
                "150.0",
                "0.6",
                "400.0",
            ],
            "Median annual wage, dollars, 2024[1]": [
                "49500",
                "120000",
                "130000",
                "100000",
            ],
            "Typical education needed for entry": [
                "-",
                "Bachelor's degree",
                "Master's degree",
                "Bachelor's degree",
            ],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Table 1.2", startrow=1, index=False)
        xw.sheets["Table 1.2"].cell(
            row=1, column=1, value="Table 1.2 Occupational projections, 2024-34"
        )


def test_parse_maps_columns_drops_summaries_and_converts_thousands(tmp_path):
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
    # Both Summary rows (00-0000 and 15-1200) dropped; only Line items remain.
    assert set(df["soc"]) == {"15-1252", "19-3094"}
    cs = df[df["soc"] == "15-1252"].iloc[0]
    assert cs["change_pct"] == 13.3  # percent, not converted
    assert cs["annual_openings"] == 150000.0  # 150.0 thousand -> actual count
    assert cs["emp_base"] == 1500000.0  # thousands -> actual
    assert cs["median_wage"] == 120000.0  # dollars, not converted
    assert cs["entry_education"] == "Bachelor's degree"
