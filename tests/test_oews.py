import numpy as np
import pandas as pd
import pytest
from src.acquire.oews import parse_oews, _to_num, _resolve_group_col


def test_to_num_handles_suppression():
    assert _to_num("48,500") == 48500.0
    assert pd.isna(_to_num("*"))
    assert pd.isna(_to_num("#"))
    assert pd.isna(_to_num(""))
    assert _to_num("123456") == 123456.0


def test_resolve_group_col_accepts_either_name():
    assert _resolve_group_col(["AREA", "O_GROUP", "TOT_EMP"]) == "O_GROUP"
    assert _resolve_group_col(["AREA", "OCC_GROUP", "TOT_EMP"]) == "OCC_GROUP"
    with pytest.raises(ValueError):
        _resolve_group_col(["AREA", "TOT_EMP"])


def _national_fixture(path):
    pd.DataFrame(
        [
            [
                "99",
                "15-1252",
                "Software Developers",
                "detailed",
                "1500000",
                "130000",
                "120000",
                "70000",
                "95000",
                "150000",
                "190000",
            ],
            [
                "99",
                "15-0000",
                "Computer Occupations",
                "major",
                "5000000",
                "100000",
                "95000",
                "",
                "",
                "",
                "",
            ],
            [
                "99",
                "19-3094",
                "Political Scientists",
                "detailed",
                "6000",
                "*",
                "*",
                "*",
                "*",
                "*",
                "*",
            ],
        ],
        columns=[
            "AREA",
            "OCC_CODE",
            "OCC_TITLE",
            "O_GROUP",
            "TOT_EMP",
            "A_MEAN",
            "A_MEDIAN",
            "A_PCT10",
            "A_PCT25",
            "A_PCT75",
            "A_PCT90",
        ],
    ).to_excel(path, index=False)


def test_parse_national_keeps_detailed_and_flags_suppression(tmp_path):
    f = tmp_path / "nat.xlsx"
    _national_fixture(f)
    df = parse_oews(f, is_metro=False)
    assert set(df["soc"]) == {"15-1252", "19-3094"}  # major row dropped
    dev = df[df["soc"] == "15-1252"].iloc[0]
    assert dev["a_median"] == 120000.0
    assert dev["national_suppressed"] == False
    pol = df[df["soc"] == "19-3094"].iloc[0]
    assert pd.isna(pol["a_median"])
    assert pol["national_suppressed"] == True


def _metro_fixture(path):
    pd.DataFrame(
        [
            [
                "47900",
                "15-1252",
                "Software Developers",
                "detailed",
                "60000",
                "140000",
                "135000",
                "80000",
                "105000",
                "160000",
                "200000",
                "1.8",
            ],
            [
                "10180",
                "15-1252",
                "Software Developers",
                "detailed",
                "2000",
                "120000",
                "118000",
                "70000",
                "90000",
                "140000",
                "180000",
                "1.1",
            ],
        ],
        columns=[
            "AREA",
            "OCC_CODE",
            "OCC_TITLE",
            "OCC_GROUP",
            "TOT_EMP",
            "A_MEAN",
            "A_MEDIAN",
            "A_PCT10",
            "A_PCT25",
            "A_PCT75",
            "A_PCT90",
            "LOC_QUOTIENT",
        ],
    ).to_excel(path, index=False)


def test_parse_metro_filters_to_dc_msa(tmp_path):
    f = tmp_path / "ma.xlsx"
    _metro_fixture(f)
    df = parse_oews(f, is_metro=True)
    assert list(df["soc"]) == ["15-1252"]  # only AREA 47900
    row = df.iloc[0]
    assert row["loc_quotient"] == 1.8
    assert row["metro_suppressed"] == False
