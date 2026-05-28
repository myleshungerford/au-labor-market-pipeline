import logging

import pandas as pd

log = logging.getLogger(__name__)


def build_mapping(completions: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    cw = crosswalk.copy()
    # CIP title lookup (first non-null title per CIP)
    titles = cw.dropna(subset=["cip_title"]).groupby("cip")["cip_title"].first()

    matched = cw.dropna(subset=["soc"])[["cip", "soc", "soc_title"]]
    rows = completions.merge(matched, on="cip", how="left")
    rows["soc_match"] = rows["soc"].notna()
    rows["program_name"] = rows["cip"].map(titles).fillna(rows["cip"])
    cols = ["cip", "program_name", "awards", "soc", "soc_title", "soc_match"]
    out = rows[cols].reset_index(drop=True)

    n_in = completions["cip"].nunique()
    n_out = out["cip"].nunique()
    assert n_in == n_out, f"CIP count changed in mapping: {n_in} -> {n_out}"
    return out
