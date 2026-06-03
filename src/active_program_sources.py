import argparse
from pathlib import Path

import pandas as pd

from src import config
from src.codes import normalize_cip
from src.program_workbook import PROGRAM_CIP_MAP_COLUMNS, PROGRAM_INVENTORY_COLUMNS


CLEAN_PROGRAM_COLUMNS = [
    "master_program_code",
    "program_name_source",
    "cip",
    "school_college",
    "program_status",
    "needs_review",
    "review_note",
]


def program_id_from_code(program_code: str) -> str:
    return (
        str(program_code)
        .strip()
        .lower()
        .replace(".", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _as_bool_value(value) -> bool:
    return str(value).strip().lower() in {"true", "yes", "y", "1"}


def _compact_note(*parts: str) -> str:
    cleaned = [str(part).strip() for part in parts if str(part).strip()]
    return " ".join(cleaned)


def _validate_clean_programs(clean_programs: pd.DataFrame) -> pd.DataFrame:
    missing = set(CLEAN_PROGRAM_COLUMNS) - set(clean_programs.columns)
    if missing:
        raise ValueError(f"Clean Program List missing columns: {sorted(missing)}")

    df = clean_programs.copy().fillna("")
    for col in CLEAN_PROGRAM_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    df["cip"] = df["cip"].map(normalize_cip)
    df = df.dropna(subset=["cip"])
    df = df[df["master_program_code"] != ""].copy()
    df["program_id"] = df["master_program_code"].map(program_id_from_code)

    duplicate_ids = df[df["program_id"].duplicated(keep=False)]["program_id"].unique()
    if len(duplicate_ids):
        raise ValueError(f"Duplicate program_id values: {sorted(duplicate_ids)}")
    return df.reset_index(drop=True)


def build_program_sources(
    clean_programs: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert the reviewed active-program master list into program workbook inputs."""
    df = _validate_clean_programs(clean_programs)
    cip_program_counts = df.groupby("cip")["program_id"].transform("nunique")

    inventory = pd.DataFrame(
        {
            "program_id": df["program_id"],
            "program_name": df["program_name_source"],
            "program_short_name": df["master_program_code"],
            "school_college": df["school_college"],
            "degree_level": "Bachelor's",
            "active_status": df["program_status"],
            "catalog_url": "",
            "program_name_source": "Active Programs by CIP.xlsx, cleaned master program list",
            "program_name_verified": "TRUE",
            "program_notes": [
                _compact_note(
                    "Generated from cleaned active-program master list.",
                    (
                        f"Cleanup review flag: {row.review_note}"
                        if _as_bool_value(row.needs_review) and row.review_note
                        else ""
                    ),
                )
                for row in df.itertuples(index=False)
            ],
        },
        columns=PROGRAM_INVENTORY_COLUMNS,
    )

    cip_map = pd.DataFrame(
        {
            "program_id": df["program_id"],
            "cip": df["cip"],
            "labor_market_cip": df["cip"],
            "cip_mapping_type": [
                "multiple_programs_share_cip" if count > 1 else "one_program_to_one_cip"
                for count in cip_program_counts
            ],
            "cip_mapping_source": "Active Programs by CIP.xlsx, cleaned master program list",
            "cip_mapping_verified": "TRUE",
            "cip_award_allocation_share": "",
            "cip_mapping_notes": [
                _compact_note(
                    (
                        f"{count} active AU programs share this CIP. Use CIP-level labor-market metrics; do not interpret IPEDS awards as program-specific without allocation data."
                        if count > 1
                        else "Single active AU program uses this CIP in the cleaned master list."
                    ),
                    (
                        f"Cleanup review flag: {row.review_note}"
                        if _as_bool_value(row.needs_review) and row.review_note
                        else ""
                    ),
                )
                for row, count in zip(df.itertuples(index=False), cip_program_counts)
            ],
        },
        columns=PROGRAM_CIP_MAP_COLUMNS,
    )

    return inventory, cip_map


def read_clean_program_workbook(path: str | Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Clean Program List", dtype=str).fillna("")


def write_program_source_csvs(
    clean_workbook_path: str | Path,
    inventory_path: str | Path = config.PROGRAM_INVENTORY_PATH,
    cip_map_path: str | Path = config.PROGRAM_CIP_MAP_PATH,
) -> tuple[Path, Path]:
    clean_programs = read_clean_program_workbook(clean_workbook_path)
    inventory, cip_map = build_program_sources(clean_programs)

    inventory_path = Path(inventory_path)
    cip_map_path = Path(cip_map_path)
    inventory.to_csv(inventory_path, index=False)
    cip_map.to_csv(cip_map_path, index=False)
    return inventory_path, cip_map_path


def main():
    parser = argparse.ArgumentParser(
        description="Build program workbook source CSVs from the cleaned active-program list."
    )
    parser.add_argument(
        "--clean-workbook",
        required=True,
        help="Path to active_programs_cleaned_<date>.xlsx.",
    )
    args = parser.parse_args()
    inventory_path, cip_map_path = write_program_source_csvs(args.clean_workbook)
    print(f"Wrote {inventory_path}")
    print(f"Wrote {cip_map_path}")


if __name__ == "__main__":
    main()
