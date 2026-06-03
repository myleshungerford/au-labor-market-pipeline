import argparse
import datetime as dt
import logging

import pandas as pd
import requests

from src import config
from src.acquire import crosswalk, ipeds, oews, projections, state_proj
from src.transform import mapping, join, aggregate
from src.excel_writer import write_workbook
from src.program_workbook import (
    build_program_onepager_data,
    load_program_cip_map,
    program_methodology,
    write_program_workbook,
)

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
    "Employment-weighting can pull summaries toward catch-all occupations; see catch_all flags, one-pager display flags, and excl-catchall wage.",
    "One-pager display flags are presentation guardrails only. Flagged occupations remain in Detail and Crosswalk Reference for auditability.",
    "Program one-pager rows are program-facing, but labor-market metrics remain CIP-level unless separate local outcome or allocation data is supplied.",
    "Active-program CIPs absent from IPEDS completions are included for program one-pager coverage, but their award counts show zero reported first-major bachelor's awards in the current IPEDS completion file, not current enrollment.",
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


def _file_date(path) -> str:
    path = config.PROJECT_ROOT / path if not hasattr(path, "exists") else path
    if not path.exists():
        return "not available"
    return dt.datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--force", action="store_true", help="ignore raw/ cache and re-download"
    )
    args = ap.parse_args()
    _setup_logging()

    cw = _cache(crosswalk.get_crosswalk(force=args.force), "crosswalk")
    comp = _cache(ipeds.get_completions(force=args.force), "completions")
    program_cip_source = load_program_cip_map()
    if not program_cip_source.empty:
        active_program_cips = pd.unique(
            pd.concat(
                [program_cip_source["cip"], program_cip_source["labor_market_cip"]]
            ).dropna()
        )
    else:
        active_program_cips = []
    proxy_cips = (
        sorted(
            set(
                program_cip_source.loc[
                    program_cip_source["labor_market_cip"] != program_cip_source["cip"],
                    "labor_market_cip",
                ]
            )
        )
        if not program_cip_source.empty
        else []
    )
    nat = _cache(oews.get_oews_national(force=args.force), "oews_national")
    metro = _cache(oews.get_oews_metro(force=args.force), "oews_metro")
    proj = _cache(projections.get_projections(force=args.force), "projections")
    # State DC/MD/VA growth is a documented proxy (spec limitation 2), not a core source.
    # If its file is not present, degrade loudly to empty state columns rather than aborting
    # the whole deliverable (national + metro remain fully populated).
    try:
        state = _cache(
            state_proj.get_state_projections(force=args.force), "state_projections"
        )
    except (FileNotFoundError, requests.exceptions.RequestException) as exc:
        # Source unreachable -> degrade loudly. (Guardrail ValueErrors are NOT caught here;
        # a coverage/vintage shift hard-fails the build by design.)
        log.warning(
            "STATE PROXY UNAVAILABLE, proceeding with empty DC/MD/VA columns: %s", exc
        )
        state = pd.DataFrame(
            columns=["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]
        )
        _cache(state, "state_projections")

    m = _cache(
        mapping.build_mapping(comp, cw, additional_cips=active_program_cips),
        "mapping",
    )
    detail = _cache(join.build_detail(m, nat, metro, proj, state), "detail")
    summary = _cache(aggregate.build_summary(detail), "summary")

    expected_cips = set(comp["cip"].dropna()) | set(active_program_cips)
    summary_cips = set(summary["cip"].dropna())
    assert expected_cips == summary_cips, (
        "CIP coverage changed between source universe and summary: "
        f"missing={sorted(expected_cips - summary_cips)} "
        f"unexpected={sorted(summary_cips - expected_cips)}"
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

    crosswalk_used = m[
        [
            "cip",
            "program_name",
            "program_short_name",
            "cip_title",
            "program_name_note",
            "soc",
            "soc_title",
        ]
    ].drop_duplicates()
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
        (
            "CIP coverage",
            f"Summary includes {comp['cip'].nunique()} CIPs with AU first-major bachelor's completions and {len(set(active_program_cips) - set(comp['cip']))} additional active-program CIPs from {config.PROGRAM_CIP_MAP_PATH.name}. Additional active-program CIPs are retained with zero reported IPEDS awards for the 2022-23 conferral year.",
        ),
        (
            "Labor-market proxy CIPs",
            (
                f"{', '.join(proxy_cips)} appear in this workbook as representative labor-market proxies for active programs whose reported CIP is a residual code with no occupational crosswalk match; AU files no completions under them (0 awards). See au_program_onepager_data for the program-to-proxy mapping and per-program disclosure."
                if proxy_cips
                else "None in this run."
            ),
        ),
        ("IPEDS Completions URL", config.IPEDS_COMPLETIONS_URL),
        (
            "IPEDS Completions download date",
            _file_date(config.RAW_DIR / f"{config.IPEDS_COMPLETIONS_FILE}.zip"),
        ),
        ("CIP-SOC crosswalk", "CIP2020_SOC2018 (NCES)"),
        ("CIP-SOC crosswalk URL", config.CROSSWALK_URL),
        (
            "CIP-SOC crosswalk download date",
            _file_date(config.RAW_DIR / "CIP2020_SOC2018_Crosswalk.xlsx"),
        ),
        (
            "OEWS",
            "May 2025 reference period (released May 2026); national + DC MSA 47900",
        ),
        ("OEWS national URL", config.OEWS_NATIONAL_URL),
        (
            "OEWS national download date",
            _file_date(config.RAW_DIR / config.OEWS_NATIONAL_ZIP),
        ),
        ("OEWS metro URL", config.OEWS_METRO_URL),
        (
            "OEWS metro download date",
            _file_date(config.RAW_DIR / config.OEWS_METRO_ZIP),
        ),
        ("National projections", "BLS Employment Projections 2024-34"),
        ("National projections URL", config.PROJECTIONS_URL),
        (
            "National projections download date",
            _file_date(config.RAW_DIR / "ep_occupation_2024_34.xlsx"),
        ),
        ("State projections", state_note),
        ("State projections landing page", config.STATE_PROJECTIONS_URL),
        (
            "State projections CSV endpoint",
            config.STATE_PROJECTIONS_CSV_ENDPOINT,
        ),
        (
            "State projections download date",
            _file_date(
                config.RAW_DIR / f"projections_central_longterm_{dt.date.today()}.csv"
            )
            if not state.empty
            else "not included in this run",
        ),
        (
            "Governance",
            "All sources public, aggregate, non-PII government data; no FERPA exposure.",
        ),
        (
            "Summed openings",
            "Addressable opportunity across associated occupations, NOT exclusive to the major.",
        ),
        (
            "One-pager display rule",
            f"Broad residual occupations (SOC titles ending in All Other and 11-1021 General and Operations Managers) are marked do_not_display_on_one_pager, but only when the CIP already has at least {config.ONE_PAGER_MIN_REAL_OCCUPATIONS} non-catch-all matched occupations. For data-poor CIPs the catch-all is surfaced so the one-pager is not left blank. All occupations remain in the Detail sheet for auditability.",
        ),
        (
            "Program display names",
            "The CIP workbook is keyed by CIP. AU-facing program names belong in the separate program one-pager dataset, which joins verified local program inventory to this CIP-level labor-market data.",
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
        "DONE: %d CIP summary rows, %d detail rows -> %s",
        summary.shape[0],
        detail.shape[0],
        out,
    )

    program_summary, program_occ, program_inventory, program_cip_map = (
        build_program_onepager_data(summary, detail)
    )
    _cache(program_summary, "program_onepager_summary")
    _cache(program_occ, "program_onepager_occupations")
    program_out = write_program_workbook(
        program_summary,
        program_occ,
        program_inventory,
        program_cip_map,
        program_methodology(),
        config.OUTPUT_DIR / f"au_program_onepager_data_{dt.date.today()}.xlsx",
    )
    log.info(
        "DONE: %d program one-pager rows, %d occupation rows -> %s",
        program_summary.shape[0],
        program_occ.shape[0],
        program_out,
    )


if __name__ == "__main__":
    main()
