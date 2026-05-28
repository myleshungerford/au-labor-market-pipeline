import argparse
import datetime as dt
import logging

import pandas as pd

from src import config
from src.acquire import crosswalk, ipeds, oews, projections, state_proj
from src.transform import mapping, join, aggregate
from src.excel_writer import write_workbook

log = logging.getLogger("run")

SPOT_CHECK = {
    "11.0701": "Computer Science",
    "45.0601": "Economics",
    "45.1001": "Political Science",
}

LIMITATIONS = [
    "CIP-SOC crosswalk is expert-judgment-based, not derived from actual graduate outcomes.",
    "Metro projections are not published; state DC/MD/VA 2022-32 used as proxy (national EP is 2024-34; base years differ).",
    "Some metro OEWS estimates are suppressed (shown as null, not zero).",
    "Crosswalk is many-to-many; summary obscures range. Detail sheet is the source of truth.",
    "Employment-weighting can pull summaries toward catch-all occupations; see catch_all flags and excl-catchall wage.",
    "BLS projections assume no major structural disruptions; AI impacts modeled conservatively.",
    "OEWS covers wage-and-salary workers only (excludes self-employed).",
    "Data vintages are pinned (spec 3.1); pipeline fails loud rather than substituting a release.",
    "Summed annual openings span all occupations a major maps to; addressable opportunity, not exclusive to the major.",
]


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_DIR / f"run_{dt.date.today()}.log"),
        ],
    )


def _cache(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_parquet(config.PROCESSED_DIR / f"{name}.parquet", index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--force", action="store_true", help="ignore raw/ cache and re-download"
    )
    args = ap.parse_args()
    _setup_logging()

    cw = _cache(crosswalk.get_crosswalk(), "crosswalk")
    comp = _cache(ipeds.get_completions(), "completions")
    nat = _cache(oews.get_oews_national(), "oews_national")
    metro = _cache(oews.get_oews_metro(), "oews_metro")
    proj = _cache(projections.get_projections(), "projections")
    # State DC/MD/VA growth is a documented proxy (spec limitation 2), not a core source.
    # If its file is not present, degrade loudly to empty state columns rather than aborting
    # the whole deliverable (national + metro remain fully populated).
    try:
        state = _cache(state_proj.get_state_projections(), "state_projections")
    except FileNotFoundError as exc:
        log.warning(
            "STATE PROXY UNAVAILABLE, proceeding with empty DC/MD/VA columns: %s", exc
        )
        state = pd.DataFrame(
            columns=["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]
        )
        _cache(state, "state_projections")

    m = _cache(mapping.build_mapping(comp, cw), "mapping")
    detail = _cache(join.build_detail(m, nat, metro, proj, state), "detail")
    summary = _cache(aggregate.build_summary(detail), "summary")

    assert comp["cip"].nunique() == summary["cip"].nunique(), (
        "AU program dropped between completions and summary"
    )

    for cip, label in SPOT_CHECK.items():
        row = summary[summary["cip"] == cip]
        if row.empty:
            log.warning(
                "spot-check %s (%s) not in AU completions this year", cip, label
            )
        else:
            r = row.iloc[0]
            log.info(
                "SPOT %s %s: occ=%s wage_nat=%s growth=%s openings=%s",
                cip,
                label,
                r["occupation_count"],
                r["wtd_median_wage_national"],
                r["wtd_growth_pct_national"],
                r["total_annual_openings"],
            )

    crosswalk_used = m[["cip", "program_name", "soc", "soc_title"]].drop_duplicates()
    state_note = (
        "Projections Central long-term 2022-32 (DC/MD/VA proxy; different base year from national)"
        if not state.empty
        else "State DC/MD/VA proxy NOT included in this run (source pending); national and metro figures are complete."
    )
    methodology = [
        ("Generated", dt.date.today().isoformat()),
        (
            "IPEDS Completions",
            f"{config.IPEDS_COMPLETIONS_FILE} (Final 2023-24 collection; degrees conferred Jul 2022-Jun 2023)",
        ),
        ("CIP-SOC crosswalk", "CIP2020_SOC2018 (NCES)"),
        (
            "OEWS",
            "May 2025 reference period (released May 2026); national + DC MSA 47900",
        ),
        ("National projections", "BLS Employment Projections 2024-34"),
        ("State projections", state_note),
        (
            "Governance",
            "All sources public, aggregate, non-PII government data; no FERPA exposure.",
        ),
        (
            "Summed openings",
            "Addressable opportunity across associated occupations, NOT exclusive to the major.",
        ),
    ]
    methodology += [(f"Limitation {i + 1}", text) for i, text in enumerate(LIMITATIONS)]

    out = write_workbook(
        summary,
        detail,
        crosswalk_used,
        methodology,
        config.OUTPUT_DIR / f"au_labor_market_{dt.date.today()}.xlsx",
    )
    log.info(
        "DONE: %d programs, %d detail rows -> %s",
        summary.shape[0],
        detail.shape[0],
        out,
    )


if __name__ == "__main__":
    main()
