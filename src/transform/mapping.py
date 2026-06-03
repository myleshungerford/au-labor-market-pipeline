import logging

import pandas as pd

from src.codes import normalize_cip

log = logging.getLogger(__name__)


def _additional_cip_frame(additional_cips) -> pd.DataFrame:
    if additional_cips is None:
        return pd.DataFrame(columns=["cip"])
    if isinstance(additional_cips, pd.DataFrame):
        if "cip" not in additional_cips.columns:
            raise ValueError("additional_cips DataFrame must include a cip column")
        values = additional_cips["cip"]
    else:
        values = pd.Series(additional_cips)
    cips = values.map(normalize_cip).dropna().drop_duplicates()
    return pd.DataFrame({"cip": sorted(cips)})


def _completion_universe(
    completions: pd.DataFrame, additional_cips=None
) -> pd.DataFrame:
    rows = completions.copy()
    rows["cip"] = rows["cip"].map(normalize_cip)
    rows = rows.dropna(subset=["cip"])
    if "awards_source_note" not in rows.columns:
        rows["awards_source_note"] = (
            "IPEDS first-major bachelor's awards, 2022-23 conferral year."
        )
    if "cip_in_ipeds_completions" not in rows.columns:
        rows["cip_in_ipeds_completions"] = True

    extra = _additional_cip_frame(additional_cips)
    missing = extra[~extra["cip"].isin(rows["cip"])]
    if not missing.empty:
        missing = missing.assign(
            awards=0,
            awards_source_note=(
                "Active-program CIP from local inventory; no first-major bachelor's awards found in IPEDS C2023_A."
            ),
            cip_in_ipeds_completions=False,
        )
        for col in rows.columns:
            if col not in missing.columns:
                missing[col] = pd.NA
        rows = pd.concat([rows, missing[rows.columns]], ignore_index=True)
    return rows.sort_values("cip").reset_index(drop=True)


def build_mapping(
    completions: pd.DataFrame, crosswalk: pd.DataFrame, additional_cips=None
) -> pd.DataFrame:
    completions = _completion_universe(completions, additional_cips)
    cw = crosswalk.copy()
    # CIP title lookup (first non-null title per CIP)
    titles = cw.dropna(subset=["cip_title"]).groupby("cip")["cip_title"].first()

    matched = cw.dropna(subset=["soc"])[["cip", "soc", "soc_title"]]
    rows = completions.merge(matched, on="cip", how="left")
    rows["soc_match"] = rows["soc"].notna()
    rows["cip_title"] = rows["cip"].map(titles).fillna(rows["cip"])
    rows["program_name"] = rows["cip_title"]
    rows["program_short_name"] = ""
    rows["program_name_note"] = ""
    cols = [
        "cip",
        "program_name",
        "program_short_name",
        "cip_title",
        "program_name_note",
        "awards",
        "cip_in_ipeds_completions",
        "awards_source_note",
        "soc",
        "soc_title",
        "soc_match",
    ]
    out = rows[cols].reset_index(drop=True)

    n_in = completions["cip"].nunique()
    n_out = out["cip"].nunique()
    assert n_in == n_out, f"CIP count changed in mapping: {n_in} -> {n_out}"
    return out
