import pandas as pd
from src.codes import normalize_cip, normalize_soc


def test_normalize_cip_pads_and_formats():
    assert normalize_cip("11.0701") == "11.0701"
    assert normalize_cip(11.0701) == "11.0701"
    assert normalize_cip("1.0") == "01.0000"  # leading zero + decimal padding
    assert normalize_cip("45.06") == "45.0600"


def test_normalize_cip_handles_missing():
    assert normalize_cip(None) is pd.NA
    assert normalize_cip("") is pd.NA
    assert normalize_cip("nan") is pd.NA


def test_normalize_soc_strips_and_uppercases():
    assert normalize_soc(" 15-1252 ") == "15-1252"
    assert (
        normalize_soc("15-1252.00") == "15-1252"
    )  # drop OEWS detailed suffix if present
