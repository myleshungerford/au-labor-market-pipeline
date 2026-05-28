import pandas as pd
from src.transform.mapping import build_mapping


def test_mapping_expands_and_flags_no_match():
    completions = pd.DataFrame({"cip": ["11.0701", "30.9999"], "awards": [42, 7]})
    crosswalk = pd.DataFrame(
        {
            "cip": ["11.0701", "11.0701", "30.9999"],
            "cip_title": [
                "Computer Science",
                "Computer Science",
                "Multi/Interdisciplinary",
            ],
            "soc": ["15-1252", "15-1211", pd.NA],
            "soc_title": ["Software Developers", "Computer Systems Analysts", pd.NA],
        }
    )
    m = build_mapping(completions, crosswalk)
    cs = m[m["cip"] == "11.0701"]
    assert sorted(cs["soc"]) == ["15-1211", "15-1252"]
    assert cs["soc_match"].all()
    assert (cs["program_name"] == "Computer Science").all()
    nomatch = m[m["cip"] == "30.9999"]
    assert len(nomatch) == 1
    assert nomatch.iloc[0]["soc_match"] == False
    assert pd.isna(nomatch.iloc[0]["soc"])


def test_no_au_program_is_dropped():
    completions = pd.DataFrame({"cip": ["11.0701", "99.9999"], "awards": [42, 1]})
    crosswalk = pd.DataFrame(
        {
            "cip": ["11.0701"],
            "cip_title": ["CS"],
            "soc": ["15-1252"],
            "soc_title": ["Dev"],
        }
    )
    m = build_mapping(completions, crosswalk)
    assert set(m["cip"]) == {
        "11.0701",
        "99.9999",
    }  # CIP absent from crosswalk still kept
