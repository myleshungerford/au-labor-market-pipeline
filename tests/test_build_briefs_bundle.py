from src.build_briefs_bundle import select_new_records


def test_select_new_records_returns_only_unknown_ids():
    records = [{"id": "a", "x": 1}, {"id": "b"}, {"id": "c"}]
    assert select_new_records({"a", "c"}, records) == [{"id": "b"}]


def test_select_new_records_preserves_workbook_order():
    records = [{"id": "z"}, {"id": "a"}, {"id": "m"}]
    assert select_new_records(set(), records) == records


def test_select_new_records_empty_when_all_known():
    records = [{"id": "a"}, {"id": "b"}]
    assert select_new_records({"a", "b"}, records) == []
