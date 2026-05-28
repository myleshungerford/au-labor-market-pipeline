import pandas as pd
from src.acquire.crosswalk import parse_crosswalk


def _make_fixture(path):
    # Mirror the real NCES workbook: a 'CIP-SOC' matched sheet plus an
    # 'Unmatched CIP Codes' sheet where SOC is 99-9999 / NO MATCH.
    with pd.ExcelWriter(path) as xw:
        pd.DataFrame(
            {
                "CIP2020Code": ["11.0701", "11.0701", "45.1001"],
                "CIP2020Title": [
                    "Computer Science.",
                    "Computer Science.",
                    "Political Science.",
                ],
                "SOC2018Code": ["15-1252", "15-1211", "19-3094"],
                "SOC2018Title": [
                    "Software Developers",
                    "Computer Systems Analysts",
                    "Political Scientists",
                ],
            }
        ).to_excel(xw, sheet_name="CIP-SOC", index=False)
        pd.DataFrame(
            {
                "CIP2020Code": ["30.9999"],
                "CIP2020Title": ["Other Multi/Interdisc."],
                "SOC2018Code": ["99-9999"],
                "SOC2018Title": ["NO MATCH"],
            }
        ).to_excel(xw, sheet_name="Unmatched CIP Codes", index=False)


def test_parse_expands_and_normalizes(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    assert set(df.columns) == {"cip", "cip_title", "soc", "soc_title"}
    cs = df[df["cip"] == "11.0701"]
    assert sorted(cs["soc"]) == ["15-1211", "15-1252"]
    assert (cs["cip_title"] == "Computer Science").all()  # trailing period stripped


def test_no_match_rows_have_na_soc(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    pol = df[df["cip"] == "30.9999"]
    assert len(pol) == 1
    assert pd.isna(pol.iloc[0]["soc"])
