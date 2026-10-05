import csv
from zipfile import ZipFile

import pytest
from pypdf import PdfReader, PdfWriter

from src import program_briefs

from src.program_briefs import (
    ProgramBriefsError,
    create_delivery_archive,
    load_program_names,
    safe_filename,
    split_full_set,
)


def test_safe_filename_preserves_readable_program_name():
    assert (
        safe_filename("Language and Area Studies: French/Europe (BA)")
        == "Language and Area Studies- French-Europe (BA)"
    )


def _write_inventory(tmp_path, names):
    inventory = tmp_path / "program_inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["program_name"])
        writer.writeheader()
        writer.writerows([{"program_name": name} for name in names])
    return inventory


def test_load_program_names_follows_bundle_order_not_alphabetical(tmp_path, monkeypatch):
    # An appended brief keeps its place at the end; nothing is re-sorted.
    inventory = _write_inventory(tmp_path, ["Accounting (BS)", "Zoology (BS)"])
    monkeypatch.setattr(
        program_briefs,
        "extract_programs2",
        lambda _: [{"name": "Zoology (BS)"}, {"name": "Accounting (BS)"}],
    )

    assert load_program_names(inventory, tmp_path / "bundle.html") == [
        "Zoology (BS)",
        "Accounting (BS)",
    ]


def test_load_program_names_rejects_bundle_inventory_mismatch(tmp_path, monkeypatch):
    inventory = _write_inventory(tmp_path, ["Accounting (BS)", "Zoology (BS)"])
    monkeypatch.setattr(
        program_briefs, "extract_programs2", lambda _: [{"name": "Accounting (BS)"}]
    )

    with pytest.raises(ProgramBriefsError, match="disagree"):
        load_program_names(inventory, tmp_path / "bundle.html")


def test_split_full_set_replaces_stale_files_with_one_page_per_program(tmp_path):
    full_set = tmp_path / "full-set.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with full_set.open("wb") as stream:
        writer.write(stream)

    destination = tmp_path / "briefs"
    destination.mkdir()
    (destination / "obsolete.pdf").write_bytes(b"obsolete")

    outputs = split_full_set(full_set, ["Accounting (BS)", "Zoology (BS)"], destination)

    assert [output.name for output in outputs] == [
        "001 - Accounting (BS).pdf",
        "002 - Zoology (BS).pdf",
    ]
    assert sorted(path.name for path in destination.glob("*.pdf")) == [
        "001 - Accounting (BS).pdf",
        "002 - Zoology (BS).pdf",
    ]
    assert all(len(PdfReader(output).pages) == 1 for output in outputs)


def test_create_delivery_archive_contains_each_program_pdf(tmp_path):
    briefs = tmp_path / "program-labor-market-briefs"
    briefs.mkdir()
    outputs = []
    for number, name in enumerate(["Accounting (BS)", "Zoology (BS)"], start=1):
        output = briefs / f"{number:03d} - {name}.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with output.open("wb") as stream:
            writer.write(stream)
        outputs.append(output)

    archive = create_delivery_archive(outputs, tmp_path / "briefs.zip")

    with ZipFile(archive) as bundle:
        assert bundle.namelist() == [
            "program-labor-market-briefs/001 - Accounting (BS).pdf",
            "program-labor-market-briefs/002 - Zoology (BS).pdf",
        ]
