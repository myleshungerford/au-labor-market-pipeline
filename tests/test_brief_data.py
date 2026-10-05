import glob
from pathlib import Path

import pytest

from src import config
from src.brief_bundle import extract_programs2
from src.brief_data import build_programs2

pytestmark = pytest.mark.skipif(
    not Path(config.PROGRAM_BRIEFS_TEMPLATE_PATH).is_file(),
    reason="brief print source is kept local, not in the repository",
)


def _latest_onepager_workbook():
    hits = sorted(glob.glob("output/au_program_onepager_data_*.xlsx"))
    assert hits, "No au_program_onepager_data workbook in output/."
    return hits[-1]


def _golden_by_id():
    return {r["id"]: r for r in extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)}


def _built_by_id():
    return {r["id"]: r for r in build_programs2(_latest_onepager_workbook())}


def test_reproduces_accounting_record_exactly():
    assert _built_by_id()["bs_acct"] == _golden_by_id()["bs_acct"]


def test_reproduces_every_existing_record_exactly():
    built = _built_by_id()
    golden = _golden_by_id()
    mismatches = [pid for pid, rec in golden.items() if built.get(pid) != rec]
    assert not mismatches, f"records differ from the committed bundle: {mismatches}"
