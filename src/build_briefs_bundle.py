"""Splice any program missing from the briefs bundle in from the one-pager workbook.

Run after ``python -m src.run`` has refreshed the one-pager workbook. This regenerates
each program's ``PROGRAMS2`` record from that workbook and inserts every program not
already baked into the bundle, leaving the existing records and all other assets
untouched. It is the repeatable, surgical path for adding programs (such as the two
non-offered fields added in this pass) without rebuilding the whole bundle from
source. See docs/superpowers/specs/2026-08-28-hypothetical-program-briefs-design.md.
"""

import argparse
import glob
import logging
from pathlib import Path

from src import config
from src.brief_bundle import extract_programs2, splice_programs2
from src.brief_data import build_programs2

log = logging.getLogger(__name__)


def latest_onepager_workbook() -> Path:
    hits = sorted(glob.glob(str(config.OUTPUT_DIR / "au_program_onepager_data_*.xlsx")))
    if not hits:
        raise FileNotFoundError(
            "No au_program_onepager_data workbook in output/. Run `python -m src.run` first."
        )
    return Path(hits[-1])


def select_new_records(existing_ids: set[str], records: list[dict]) -> list[dict]:
    """Return the workbook records whose id is not already in the bundle (in order)."""
    return [record for record in records if record["id"] not in existing_ids]


def add_missing_records(template_path: Path, workbook_path: Path) -> list[dict]:
    """Splice every workbook program missing from the bundle; return the added records."""
    existing_ids = {record["id"] for record in extract_programs2(template_path)}
    new_records = select_new_records(existing_ids, build_programs2(workbook_path))
    if new_records:
        splice_programs2(template_path, new_records, template_path)
    return new_records


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template", type=Path, default=config.PROGRAM_BRIEFS_TEMPLATE_PATH
    )
    parser.add_argument("--workbook", type=Path, default=None)
    args = parser.parse_args()

    workbook = args.workbook or latest_onepager_workbook()
    added = add_missing_records(args.template, workbook)
    if added:
        names = ", ".join(f"{r['name']} (CIP {r['cip']})" for r in added)
        log.info("Added %d program(s) to %s: %s", len(added), args.template.name, names)
    else:
        log.info("No new programs; %s already current.", args.template.name)


if __name__ == "__main__":
    main()
