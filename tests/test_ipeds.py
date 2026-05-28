import pandas as pd
from src.acquire.ipeds import parse_completions


def _fixture(path):
    pd.DataFrame(
        [
            # unitid, cipcode, majornum, awlevel, ctotalt
            [131159, "11.0701", 1, 5, 42],  # keep: CS bachelor's first major
            [131159, "45.0601", 1, 5, 30],  # keep: Economics
            [131159, "11.0701", 2, 5, 5],  # drop: second major
            [131159, "45.1001", 1, 3, 10],  # drop: not bachelor's (awlevel 3)
            [131159, "99", 1, 5, 999],  # drop: grand total CIP
            [131159, "26.0101", 1, 5, 0],  # drop: zero awards
            [999999, "11.0701", 1, 5, 88],  # drop: other institution
        ],
        columns=["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"],
    ).to_csv(path, index=False)


def test_parse_filters_to_au_bachelors_first_major(tmp_path):
    f = tmp_path / "c.csv"
    _fixture(f)
    df = parse_completions(f)
    assert set(df.columns) == {"cip", "awards"}
    assert sorted(df["cip"]) == ["11.0701", "45.0601"]
    assert int(df[df["cip"] == "11.0701"]["awards"].iloc[0]) == 42
