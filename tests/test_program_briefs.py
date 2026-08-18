import csv

from pypdf import PdfReader, PdfWriter

from src.program_briefs import load_program_names, safe_filename, split_full_set


def test_safe_filename_preserves_readable_program_name():
    assert (
        safe_filename("Language and Area Studies: French/Europe (BA)")
        == "Language and Area Studies- French-Europe (BA)"
    )


def test_load_program_names_sorts_verified_inventory(tmp_path):
    inventory = tmp_path / "program_inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["program_name"])
        writer.writeheader()
        writer.writerows(
            [{"program_name": "Zoology (BS)"}, {"program_name": "Accounting (BS)"}]
        )

    assert load_program_names(inventory) == ["Accounting (BS)", "Zoology (BS)"]


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
