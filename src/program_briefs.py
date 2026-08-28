"""Build and synchronize the program labor-market brief PDFs.

The HTML print source is rendered once, then the resulting full set is split into
one page per verified program name. This makes the full-set PDF and its individual
briefs a single build product rather than two independently maintained artifacts.
"""

import argparse
import csv
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader, PdfWriter

from src import config


class ProgramBriefsError(RuntimeError):
    """Raised when the brief render or synchronization cannot be verified."""


def safe_filename(value: str) -> str:
    """Return a Windows-safe, readable filename stem."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "-", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        raise ProgramBriefsError("A program name produced an empty filename.")
    return cleaned


def load_program_names(inventory_path: Path = config.PROGRAM_INVENTORY_PATH) -> list[str]:
    """Read the verified names in the same alphabetical order as the brief set."""
    with inventory_path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    names = [row.get("program_name", "").strip() for row in rows]
    if not names or any(not name for name in names):
        raise ProgramBriefsError(
            f"{inventory_path} must contain a non-empty program_name for every row."
        )
    if len(names) != len(set(names)):
        raise ProgramBriefsError("Program inventory contains duplicate program names.")
    return sorted(names, key=str.casefold)


def split_full_set(
    full_set_path: Path,
    program_names: list[str],
    destination: Path = config.PROGRAM_BRIEFS_DIR,
) -> list[Path]:
    """Replace the individual PDFs with one exact page from the full-set PDF each."""
    reader = PdfReader(full_set_path)
    if len(reader.pages) != len(program_names):
        raise ProgramBriefsError(
            f"Full set has {len(reader.pages)} pages, but inventory has "
            f"{len(program_names)} programs. No individual PDFs were changed."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="program-briefs-", dir=destination.parent))
    try:
        outputs: list[Path] = []
        for number, (program_name, page) in enumerate(
            zip(program_names, reader.pages, strict=True), start=1
        ):
            output = destination / f"{number:03d} - {safe_filename(program_name)}.pdf"
            staged_output = staging / output.name
            writer = PdfWriter()
            writer.add_page(page)
            with staged_output.open("wb") as stream:
                writer.write(stream)
            outputs.append(output)

        for staged_output, output in zip(sorted(staging.glob("*.pdf")), outputs, strict=True):
            if len(PdfReader(staged_output).pages) != 1:
                raise ProgramBriefsError(f"Invalid one-page output: {staged_output.name}")

        destination.mkdir(exist_ok=True)
        expected = {output.name for output in outputs}
        for old_output in destination.glob("*.pdf"):
            if old_output.name not in expected:
                old_output.unlink()
        for output in outputs:
            os.replace(staging / output.name, output)
        return outputs
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def create_delivery_archive(
    brief_paths: list[Path],
    archive_path: Path = config.PROGRAM_BRIEFS_ARCHIVE_PATH,
) -> Path:
    """Replace the delivery ZIP with exactly the current individual program PDFs."""
    if not brief_paths:
        raise ProgramBriefsError("No program PDFs are available to package.")
    if any(not path.is_file() for path in brief_paths):
        raise ProgramBriefsError("Cannot package a missing program PDF.")

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="program-briefs-", suffix=".zip", dir=archive_path.parent, delete=False
    ) as stream:
        staged_archive = Path(stream.name)
    try:
        with ZipFile(staged_archive, "w", compression=ZIP_DEFLATED) as archive:
            for brief_path in sorted(brief_paths, key=lambda path: path.name):
                archive.write(brief_path, arcname=f"{brief_path.parent.name}/{brief_path.name}")
        os.replace(staged_archive, archive_path)
    finally:
        staged_archive.unlink(missing_ok=True)
    return archive_path


def current_program_briefs(
    program_names: list[str], destination: Path = config.PROGRAM_BRIEFS_DIR
) -> list[Path]:
    """Return the expected individual PDFs without altering a direct PDF correction."""
    briefs = [
        destination / f"{number:03d} - {safe_filename(name)}.pdf"
        for number, name in enumerate(program_names, start=1)
    ]
    missing = [path.name for path in briefs if not path.is_file()]
    if missing:
        raise ProgramBriefsError(
            f"Cannot package incomplete briefs. Missing: {', '.join(missing)}"
        )
    return briefs


def find_chrome(chrome_override: Path | None = None) -> Path:
    """Locate Chrome, which produced the existing full-set PDF."""
    candidates = [chrome_override] if chrome_override else []
    candidates.extend(
        [
            Path(os.environ["PROGRAM_BRIEFS_CHROME"])
            if "PROGRAM_BRIEFS_CHROME" in os.environ
            else None,
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise ProgramBriefsError(
        "Google Chrome was not found. Pass --chrome-path or set PROGRAM_BRIEFS_CHROME."
    )


def render_html_to_pdf(html_path: Path, output_pdf: Path, chrome_path: Path) -> None:
    """Print the self-contained HTML source to a PDF after its client content loads."""
    if not html_path.is_file():
        raise ProgramBriefsError(f"Brief HTML source not found: {html_path}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="program-briefs-chrome-") as profile:
        command = [
            str(chrome_path),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--virtual-time-budget=10000",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={output_pdf}",
            html_path.resolve().as_uri(),
        ]
        subprocess.run(command, check=True, timeout=60, capture_output=True, text=True)

    if not output_pdf.is_file() or output_pdf.stat().st_size == 0:
        raise ProgramBriefsError("Chrome did not produce a full-set PDF.")


def build_from_html(
    html_path: Path,
    chrome_path: Path | None = None,
    full_set_path: Path = config.PROGRAM_BRIEFS_FULL_SET_PATH,
    destination: Path = config.PROGRAM_BRIEFS_DIR,
    inventory_path: Path = config.PROGRAM_INVENTORY_PATH,
) -> list[Path]:
    """Render the full set and synchronize every program PDF from the same render."""
    program_names = load_program_names(inventory_path)
    full_set_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="program-briefs-build-", dir=full_set_path.parent) as temp_dir:
        rendered = Path(temp_dir) / full_set_path.name
        render_html_to_pdf(html_path, rendered, find_chrome(chrome_path))
        outputs = split_full_set(rendered, program_names, destination)
        os.replace(rendered, full_set_path)
        create_delivery_archive(outputs)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render and synchronize the program labor-market brief PDFs."
    )
    parser.add_argument(
        "--source-html",
        type=Path,
        default=config.PROGRAM_BRIEFS_TEMPLATE_PATH,
        help="self-contained HTML print source (defaults to templates/)",
    )
    parser.add_argument(
        "--chrome-path", type=Path, help="path to chrome.exe when auto-detection fails"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--split-only",
        action="store_true",
        help="refresh individual PDFs from the existing full set without rendering HTML",
    )
    mode.add_argument(
        "--package-only",
        action="store_true",
        help="refresh the delivery ZIP without changing the individual PDFs",
    )
    args = parser.parse_args()

    if args.split_only:
        outputs = split_full_set(
            config.PROGRAM_BRIEFS_FULL_SET_PATH,
            load_program_names(),
            config.PROGRAM_BRIEFS_DIR,
        )
        archive = create_delivery_archive(outputs)
    elif args.package_only:
        outputs = current_program_briefs(load_program_names())
        archive = create_delivery_archive(outputs)
    else:
        outputs = build_from_html(args.source_html, args.chrome_path)
        archive = config.PROGRAM_BRIEFS_ARCHIVE_PATH
    print(f"Synchronized {len(outputs)} program briefs in {config.PROGRAM_BRIEFS_DIR}")
    print(f"Created delivery archive: {archive}")


if __name__ == "__main__":
    main()
