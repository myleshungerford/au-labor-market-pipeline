import datetime as dt
import logging
from pathlib import Path

import pandas as pd

from src import config
from src.codes import normalize_cip

log = logging.getLogger(__name__)

PROGRAM_INVENTORY_COLUMNS = [
    "program_id",
    "program_name",
    "program_short_name",
    "school_college",
    "degree_level",
    "active_status",
    "catalog_url",
    "program_name_source",
    "program_name_verified",
    "program_notes",
]
# Optional reader-facing sentence the brief prints under "How to read this". Optional
# so an inventory regenerated from the master program list (which has no such column)
# still loads; a missing column reads as blank.
PROGRAM_INVENTORY_OPTIONAL_COLUMNS = ["brief_note"]

PROGRAM_CIP_MAP_COLUMNS = [
    "program_id",
    "cip",
    "labor_market_cip",
    "cip_mapping_type",
    "cip_mapping_source",
    "cip_mapping_verified",
    "cip_award_allocation_share",
    "cip_mapping_notes",
]


def _read_lookup(path, columns, optional=()):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=columns + list(optional))
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
    for col in optional:
        if col not in df.columns:
            df[col] = ""
    columns = columns + list(optional)
    df = df[columns].copy()
    for col in columns:
        df[col] = df[col].astype(str).str.strip()
    return df[df[columns[0]] != ""].drop_duplicates().reset_index(drop=True)


def load_program_inventory(path=None) -> pd.DataFrame:
    path = config.PROGRAM_INVENTORY_PATH if path is None else path
    return _read_lookup(
        path, PROGRAM_INVENTORY_COLUMNS, PROGRAM_INVENTORY_OPTIONAL_COLUMNS
    )


def load_program_cip_map(path=None) -> pd.DataFrame:
    path = config.PROGRAM_CIP_MAP_PATH if path is None else path
    df = _read_lookup(path, PROGRAM_CIP_MAP_COLUMNS)
    if not df.empty:
        df["cip"] = df["cip"].map(normalize_cip)
        df = df.dropna(subset=["cip"])
        lm = df["labor_market_cip"].map(normalize_cip)
        df["labor_market_cip"] = lm.where(lm.notna(), df["cip"])
    return df.reset_index(drop=True)


def _as_bool(series):
    return series.astype(str).str.strip().str.lower().isin({"true", "yes", "y", "1"})


def _program_id_for_cip(cip):
    return f"cip_{str(cip).replace('.', '_')}"


def _default_sources(summary: pd.DataFrame):
    rows = summary[["cip"]].drop_duplicates().sort_values("cip").reset_index(drop=True)
    inventory = pd.DataFrame(
        {
            "program_id": rows["cip"].map(_program_id_for_cip),
            "program_name": "",
            "program_short_name": "",
            "school_college": "",
            "degree_level": "Bachelor's",
            "active_status": "needs_local_inventory",
            "catalog_url": "",
            "program_name_source": "not yet supplied",
            "program_name_verified": "FALSE",
            "program_notes": "Generated CIP-level placeholder. Replace with verified AU program inventory before publishing one-pagers.",
        }
    )
    cip_map = pd.DataFrame(
        {
            "program_id": inventory["program_id"],
            "cip": rows["cip"],
            "cip_mapping_type": "provisional_cip_row",
            "cip_mapping_source": "generated from IPEDS CIP row pending local inventory",
            "cip_mapping_verified": "FALSE",
            "cip_award_allocation_share": "",
            "cip_mapping_notes": "Not a verified AU program-to-CIP mapping.",
        }
    )
    return inventory, cip_map


def _prepare_sources(summary, inventory=None, cip_map=None):
    inventory = load_program_inventory() if inventory is None else inventory.copy()
    cip_map = load_program_cip_map() if cip_map is None else cip_map.copy()
    if inventory.empty or cip_map.empty:
        return _default_sources(summary)
    return inventory, cip_map


def build_program_onepager_data(
    summary: pd.DataFrame,
    detail: pd.DataFrame,
    inventory: pd.DataFrame | None = None,
    cip_map: pd.DataFrame | None = None,
):
    inventory, cip_map = _prepare_sources(summary, inventory, cip_map)

    cip_summary = summary.copy()
    if "cip_title" not in cip_summary.columns:
        cip_summary["cip_title"] = cip_summary["program_name"]
    for col in ["program_name", "program_short_name", "program_name_note"]:
        if col in cip_summary.columns:
            cip_summary = cip_summary.drop(columns=[col])
    cip_summary = cip_summary.rename(columns={"awards": "cip_awards_conferred_2022_23"})

    program_base = cip_map.merge(inventory, on="program_id", how="left")
    # labor_market_cip is an optional per-program proxy that feeds ONLY the occupation/
    # wage/openings panel. It defaults to the program's reported CIP. Awards and program
    # identity always come from the reported CIP, so award attribution is never disturbed.
    if "labor_market_cip" in program_base.columns:
        lm = program_base["labor_market_cip"].astype(str).str.strip()
        program_base["labor_market_cip"] = lm.where(lm.ne(""), program_base["cip"])
    else:
        program_base["labor_market_cip"] = program_base["cip"]

    summary_cips = set(cip_summary["cip"].dropna())
    program_base["cip_labor_market_match"] = program_base["labor_market_cip"].isin(
        summary_cips
    )
    cip_counts = program_base.groupby("cip")["program_id"].transform("nunique")
    program_base["programs_sharing_cip"] = cip_counts
    program_base["uses_shared_cip_metrics"] = cip_counts > 1
    program_base.loc[
        program_base["cip_mapping_type"].isin(
            ["provisional_cip_row", "multiple_programs_share_cip"]
        ),
        "uses_shared_cip_metrics",
    ] = True
    proxied = program_base["labor_market_cip"].ne(program_base["cip"])
    program_base["labor_market_proxy_note"] = ""
    program_base.loc[proxied, "labor_market_proxy_note"] = (
        "Labor-market data shown via representative proxy CIP "
        + program_base.loc[proxied, "labor_market_cip"].astype(str)
        + "; the reported CIP "
        + program_base.loc[proxied, "cip"].astype(str)
        + " has no occupational crosswalk match. Awards reflect the reported CIP."
    )

    # Identity and awards come from the reported CIP; labor-market metrics from the
    # (possibly proxy) labor CIP.
    identity_cols = [
        c
        for c in [
            "cip_title",
            "cip_awards_conferred_2022_23",
            "cip_in_ipeds_completions",
            "awards_source_note",
        ]
        if c in cip_summary.columns
    ]
    identity = cip_summary[["cip"] + identity_cols]
    labor = cip_summary[
        [c for c in cip_summary.columns if c not in identity_cols]
    ].rename(columns={"cip": "labor_market_cip"})
    program_summary = program_base.merge(identity, on="cip", how="left").merge(
        labor, on="labor_market_cip", how="left"
    )
    share = pd.to_numeric(
        program_summary["cip_award_allocation_share"], errors="coerce"
    )
    mapping_verified = _as_bool(program_summary["cip_mapping_verified"])
    name_verified = _as_bool(program_summary["program_name_verified"])
    one_to_one = program_summary["cip_mapping_type"].eq("one_program_to_one_cip")
    program_summary["program_awards_conferred_2022_23"] = pd.NA
    program_summary.loc[share.notna(), "program_awards_conferred_2022_23"] = (
        program_summary.loc[share.notna(), "cip_awards_conferred_2022_23"]
        * share[share.notna()]
    )
    copy_awards = share.isna() & mapping_verified & one_to_one
    program_summary.loc[copy_awards, "program_awards_conferred_2022_23"] = (
        program_summary.loc[copy_awards, "cip_awards_conferred_2022_23"]
    )
    program_summary["labor_market_data_level"] = "CIP"
    program_summary.loc[
        program_summary["labor_market_cip"].ne(program_summary["cip"]),
        "labor_market_data_level",
    ] = "CIP (proxy)"
    base_ready = (
        program_summary["program_name"].astype(str).str.strip().ne("")
        & name_verified
        & mapping_verified
    )
    ready = base_ready & program_summary["cip_labor_market_match"]
    program_summary["one_pager_ready"] = ready
    program_summary["_base_ready"] = base_ready
    program_summary["one_pager_blocker"] = program_summary.apply(
        _one_pager_blocker, axis=1
    )
    program_summary = program_summary.drop(columns=["_base_ready"])

    detail_source = detail.copy()
    for col in ["program_name", "program_short_name", "program_name_note"]:
        if col in detail_source.columns:
            detail_source = detail_source.drop(columns=[col])
    detail_source = detail_source.rename(columns={"cip": "labor_market_cip"})
    if "cip_title" in detail_source.columns:
        detail_source = detail_source.rename(columns={"cip_title": "labor_cip_title"})
    program_occupations = program_base.merge(
        detail_source, on="labor_market_cip", how="left"
    )

    summary_first = [
        "program_id",
        "program_name",
        "program_short_name",
        "school_college",
        "degree_level",
        "active_status",
        "one_pager_ready",
        "one_pager_blocker",
        "cip",
        "cip_title",
        "labor_market_cip",
        "cip_mapping_type",
        "cip_mapping_verified",
        "cip_labor_market_match",
        "programs_sharing_cip",
        "uses_shared_cip_metrics",
        "cip_awards_conferred_2022_23",
        "program_awards_conferred_2022_23",
        "cip_in_ipeds_completions",
        "awards_source_note",
        "labor_market_data_level",
        "labor_market_proxy_note",
    ]
    program_summary = _order_columns(program_summary, summary_first)

    occupation_first = [
        "program_id",
        "program_name",
        "program_short_name",
        "cip",
        "labor_market_cip",
        "cip_mapping_type",
        "cip_labor_market_match",
        "soc",
        "soc_title",
        "soc_match",
        "do_not_display_on_one_pager",
        "one_pager_display_note",
    ]
    program_occupations = _order_columns(program_occupations, occupation_first)
    return program_summary, program_occupations, inventory, cip_map


def _order_columns(df, first):
    existing_first = [c for c in first if c in df.columns]
    rest = [c for c in df.columns if c not in existing_first]
    return df[existing_first + rest]


def _one_pager_blocker(row) -> str:
    blockers = []
    if not bool(row["_base_ready"]):
        if str(row.get("labor_market_data_level", "")) == "CIP (proxy)":
            blockers.append(
                f"Labor-market proxy (CIP {row.get('labor_market_cip')}) is a builder proposal "
                "pending school/registrar confirmation; do not publish until confirmed."
            )
        else:
            blockers.append(
                "Needs verified AU program inventory and program-to-CIP mapping."
            )
    if not bool(row["cip_labor_market_match"]):
        blockers.append(
            "No CIP labor-market summary match; retain row for audit but do not publish one-pager until the CIP has source coverage or a documented no-data note."
        )
    return " ".join(blockers)


def write_program_workbook(
    program_summary,
    program_occupations,
    program_inventory,
    program_cip_map,
    methodology,
    out_path,
) -> Path:
    out_path = Path(out_path)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as xw:
        program_summary.to_excel(xw, sheet_name="Program One-Pager Data", index=False)
        program_occupations.to_excel(xw, sheet_name="Program Occupations", index=False)
        program_inventory.to_excel(xw, sheet_name="Program Inventory", index=False)
        program_cip_map.to_excel(xw, sheet_name="Program-CIP Map", index=False)
        pd.DataFrame(methodology, columns=["Item", "Detail"]).to_excel(
            xw, sheet_name="Methodology", index=False
        )

        wb = xw.book
        wrap = wb.add_format({"text_wrap": True, "valign": "top"})
        money = wb.add_format({"num_format": "$#,##0"})
        count = wb.add_format({"num_format": "#,##0"})
        for name, frame in (
            ("Program One-Pager Data", program_summary),
            ("Program Occupations", program_occupations),
            ("Program Inventory", program_inventory),
            ("Program-CIP Map", program_cip_map),
        ):
            ws = xw.sheets[name]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(len(frame), 1), max(len(frame.columns) - 1, 0))
            for i, col in enumerate(frame.columns):
                width = min(max(len(str(col)) + 2, 14), 48)
                fmt = money if ("wage" in col or "median" in col) else None
                if "awards" in col or "openings" in col or col.endswith("_count"):
                    fmt = count
                ws.set_column(i, i, width, fmt)
        xw.sheets["Methodology"].set_column(0, 0, 28)
        xw.sheets["Methodology"].set_column(1, 1, 100, wrap)
    log.info("wrote program workbook %s", out_path)
    return out_path


def program_methodology():
    return [
        ("Generated", dt.date.today().isoformat()),
        (
            "Purpose",
            "Program-facing one-pager dataset. One row represents an AU program record, while labor-market metrics remain sourced at the mapped CIP level.",
        ),
        (
            "Program inventory",
            f"Loaded from {config.PROGRAM_INVENTORY_PATH.name}. If blank, generated CIP placeholders are marked not ready for publication.",
        ),
        (
            "Active-program source",
            "program_inventory.csv and program_cip_map.csv are intended to be generated from the reviewed registrar active-program cleanup workbook with src.active_program_sources.",
        ),
        (
            "Program-CIP map",
            f"Loaded from {config.PROGRAM_CIP_MAP_PATH.name}. Shared or provisional CIPs reuse CIP-level labor-market metrics.",
        ),
        (
            "Readiness rule",
            "one_pager_ready is TRUE only when the AU program name is verified, the program-to-CIP mapping is verified, and the mapped CIP has a labor-market summary match in the current pipeline output.",
        ),
        (
            "Awards",
            "IPEDS awards are CIP-level. Program-level awards are populated only for verified one-program-to-one-CIP mappings or explicit allocation shares. Active-program CIPs absent from IPEDS completions carry an awards_source_note and zero reported awards for the 2022-23 conferral year.",
        ),
        (
            "No SOC match",
            "Programs whose mapped CIP has no standard SOC match remain in the workbook as ready rows when the no-match condition is represented in the CIP pipeline; one-pagers should use the no-standard-mapping template.",
        ),
        (
            "Labor-market data",
            "Wages, openings, growth, mapped occupations, and display flags are pulled from the CIP labor-market pipeline.",
        ),
        (
            "Labor-market proxy",
            "A program whose reported CIP is a residual code with no occupational crosswalk match may carry a labor_market_cip proxy: the occupation, wage, growth, and openings panel is drawn from a representative CIP, while the reported CIP and all award figures are unchanged. Such rows are flagged labor_market_data_level = 'CIP (proxy)' and carry a labor_market_proxy_note. The proxy lives on the program, not the CIP, so two programs sharing one reported CIP can use different proxies.",
        ),
        (
            "Non-offered fields (one-off)",
            "program_id hp_ppol (Public Policy, CIP 44.0501) and hp_padm (Public Administration, CIP 44.0401) were added 2026-08-28 as illustrative fields (not current AU undergraduate majors). American University offers neither as an undergraduate major, so both carry zero IPEDS bachelor's awards; their labor-market figures are national/DC-metro CIP data like any other program. See docs/superpowers/specs/2026-08-28-hypothetical-program-briefs-design.md.",
        ),
        (
            "Track-level brief (one-off)",
            "program_id trk_crwr (Creative Writing, CIP 23.1302) was added 2026-09-09. Creative Writing is a track within the Literature (BA), not a separately reported major, so AU files no first-major bachelor's completions under CIP 23.1302 and the row carries zero reported awards; its labor-market figures are national/DC-metro CIP data like any other program. CIP 23.1302 has four SOC crosswalk matches, one of which is a residual 'All Other' code that the display rule surfaces rather than hides because the CIP has fewer than the minimum number of non-catch-all occupations. See docs/superpowers/specs/2026-09-09-creative-writing-brief-design.md.",
        ),
        (
            "Minor-level brief (one-off)",
            "program_id mn_ltst (Latinx Studies, CIP 05.0107) was added 2026-10-05 for the LTST minor. IPEDS Completions does not report minors, so its CIP map row carries an award share of 0 and CIP 05.0107's reported awards stay with ba_spla, which shares the CIP. Its labor-market figures are national/DC-metro CIP data like any other program. CIPs 05.0107, 05.0134, and 05.0203 each map to the single SOC 25-1062 in the crosswalk, so all three yield identical figures; the brief prints that via the inventory brief_note column. See docs/superpowers/specs/2026-10-05-latinx-studies-brief-design.md.",
        ),
        (
            "Brief numbering",
            "Brief numbers are frozen as of 2026-10-05: briefs 001-084 keep their alphabetical order from 2026-09-09 and each later brief is appended as the next number, so existing numbers never shift. Page order is the PROGRAMS2 array order in the briefs bundle.",
        ),
    ]
