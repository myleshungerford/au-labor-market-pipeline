from pathlib import Path

import pytest

from src import config
from src.program_briefs import load_program_names
from src.brief_bundle import (
    _find_programs2_uuid,
    _read_manifest,
    extract_programs2,
    splice_programs2,
)

pytestmark = pytest.mark.skipif(
    not Path(config.PROGRAM_BRIEFS_TEMPLATE_PATH).is_file(),
    reason="brief print source is kept local, not in the repository",
)


def test_extract_programs2_returns_current_records_from_committed_bundle():
    records = extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)

    assert len(records) == len(load_program_names())
    by_id = {r["id"]: r for r in records}
    assert by_id["bs_acct"]["name"] == "Accounting (BS)"
    assert by_id["bs_acct"]["cip"] == "52.0301"


def test_committed_shell_prints_array_order_with_frozen_numbering():
    # Briefs 001-084 are frozen in their 2026-09-09 alphabetical order; later briefs
    # are appended, so the shell must render the array as-is rather than re-sort it.
    html = Path(config.PROGRAM_BRIEFS_TEMPLATE_PATH).read_text(encoding="utf-8")
    assert "const ALL = [...window.PROGRAMS2];" in html
    assert "localeCompare" not in html

    names = [r["name"] for r in extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)]
    assert names[:84] == sorted(names[:84], key=str.casefold)
    assert names[0] == "Accounting (BS)"
    assert names[83] == "Women's, Gender, and Sexuality Studies (BA)"


def test_committed_bundle_includes_the_two_non_offered_fields():
    by_id = {r["id"]: r for r in extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)}

    for pid, name, cip in [
        ("hp_ppol", "Public Policy", "44.0501"),
        ("hp_padm", "Public Administration", "44.0401"),
    ]:
        record = by_id[pid]
        assert record["name"] == name
        assert record["cip"] == cip
        assert record["match"] and record["ready"] and not record["isProxy"]


def test_committed_bundle_includes_creative_writing():
    by_id = {r["id"]: r for r in extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)}

    record = by_id["trk_crwr"]
    assert record["name"] == "Creative Writing"
    assert record["cip"] == "23.1302"
    assert record["match"] and record["ready"] and not record["isProxy"]
    # 4 crosswalk SOCs, one of which is a surfaced catch-all (below the hide threshold).
    assert record["occCount"] == 4
    assert record["displayedCount"] == 4
    assert record["catchall"]


def test_committed_bundle_appends_latinx_studies_as_brief_085():
    records = extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)
    record = records[84]
    assert record["id"] == "mn_ltst"
    assert record["name"] == "Latinx Studies"
    assert record["cip"] == "05.0107"
    assert record["match"] and record["ready"] and not record["isProxy"]
    assert record["singleTeaching"] and [o["soc"] for o in record["occs"]] == ["25-1062"]
    assert "05.0134" in record["note"] and "05.0203" in record["note"]
    # The only record carrying a printed note.
    assert [r["id"] for r in records if "note" in r] == ["mn_ltst"]


def test_splice_appends_records_and_preserves_existing(tmp_path):
    original = extract_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH)
    new = [{"id": "hp_test", "name": "Ztest Program", "occs": []}]
    out = tmp_path / "spliced.html"

    splice_programs2(config.PROGRAM_BRIEFS_TEMPLATE_PATH, new, out)

    result = extract_programs2(out)
    assert len(result) == len(original) + 1
    assert result[: len(original)] == original
    assert result[-1] == new[0]


def test_splice_leaves_all_other_assets_untouched(tmp_path):
    src = config.PROGRAM_BRIEFS_TEMPLATE_PATH
    out = tmp_path / "spliced.html"
    splice_programs2(src, [{"id": "hp_test", "name": "Z", "occs": []}], out)

    before = _read_manifest(Path(src).read_text(encoding="utf-8"))
    after = _read_manifest(out.read_text(encoding="utf-8"))
    data_uuid = _find_programs2_uuid(before)

    assert set(before) == set(after)
    changed = [u for u in before if before[u] != after[u]]
    assert changed == [data_uuid]
