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
    assert (cs["cip_title"] == "Computer Science").all()
    assert cs["cip_in_ipeds_completions"].all()
    assert (cs["awards_source_note"] != "").all()
    nomatch = m[m["cip"] == "30.9999"]
    assert len(nomatch) == 1
    assert nomatch.iloc[0]["program_name"] == "Multi/Interdisciplinary"
    assert nomatch.iloc[0]["cip_title"] == "Multi/Interdisciplinary"
    assert nomatch.iloc[0]["program_short_name"] == ""
    assert nomatch.iloc[0]["program_name_note"] == ""
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


def test_additional_active_cip_is_retained_with_zero_awards():
    completions = pd.DataFrame({"cip": ["11.0701"], "awards": [42]})
    crosswalk = pd.DataFrame(
        {
            "cip": ["11.0701", "50.0301"],
            "cip_title": ["CS", "Dance"],
            "soc": ["15-1252", "27-2032"],
            "soc_title": ["Dev", "Choreographers"],
        }
    )

    m = build_mapping(completions, crosswalk, additional_cips=["50.0301"])

    added = m[m["cip"] == "50.0301"].iloc[0]
    assert added["awards"] == 0
    assert added["cip_in_ipeds_completions"] == False
    assert "no first-major bachelor's awards" in added["awards_source_note"]
    assert added["program_name"] == "Dance"
