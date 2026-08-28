"""Read and patch the self-contained program-briefs HTML bundle.

The printable briefs ship as one self-contained HTML file produced by an external
bundler: assets (React, Babel, fonts, and the program data) are base64-encoded,
optionally gzip-compressed, and stored in a ``__bundler/manifest`` script tag; a
``__bundler/template`` script holds the page shell that references each asset by
UUID. The program records the briefs render from live in a ``window.PROGRAMS2``
JavaScript array inside one of those assets.

This module reads that array back out (``extract_programs2``) and writes new
records into it in place (``splice_programs2``) without disturbing any other asset,
so two hypothetical programs can be added to the existing 81 without rebuilding the
whole bundle from source.
"""

import base64
import gzip
import json
import re
from pathlib import Path

_MANIFEST_RE = re.compile(r'<script type="__bundler/manifest">(.*?)</script>', re.S)
_PROGRAMS2_MARKER = "window.PROGRAMS2"
# The data asset ASSIGNS the array; the component asset only names it in a comment
# ("Consumes one program object from window.PROGRAMS2"). Match the assignment so the
# two are never confused.
_PROGRAMS2_ASSIGN_RE = re.compile(r"window\.PROGRAMS2\s*=\s*\[")


class BriefBundleError(RuntimeError):
    """Raised when the bundle cannot be parsed or patched safely."""


def _read_manifest(html: str) -> dict:
    match = _MANIFEST_RE.search(html)
    if not match:
        raise BriefBundleError("Bundle has no __bundler/manifest script.")
    return json.loads(match.group(1))


def _decode_asset(entry: dict) -> bytes:
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw


def _find_programs2_uuid(manifest: dict) -> str:
    hits = []
    for uuid, entry in manifest.items():
        if "javascript" not in entry.get("mime", ""):
            continue
        try:
            text = _decode_asset(entry).decode("utf-8", "ignore")
        except Exception:  # pragma: no cover - a corrupt asset is not the data asset
            continue
        if _PROGRAMS2_ASSIGN_RE.search(text):
            hits.append(uuid)
    if len(hits) != 1:
        raise BriefBundleError(
            f"Expected exactly one asset assigning {_PROGRAMS2_MARKER}, found {len(hits)}."
        )
    return hits[0]


def _parse_programs2_array(js: str) -> list[dict]:
    marker = js.index(_PROGRAMS2_MARKER)
    start = js.index("[", marker)
    end = js.rindex("]")
    return json.loads(js[start : end + 1])


def extract_programs2(template_path: Path) -> list[dict]:
    """Return the ``window.PROGRAMS2`` records currently baked into the bundle."""
    html = Path(template_path).read_text(encoding="utf-8")
    manifest = _read_manifest(html)
    uuid = _find_programs2_uuid(manifest)
    js = _decode_asset(manifest[uuid]).decode("utf-8")
    return _parse_programs2_array(js)


def _reencode_asset(entry: dict, text: str) -> str:
    raw = text.encode("utf-8")
    if entry.get("compressed"):
        # mtime=0 keeps the output stable across runs; the loader only decompresses.
        raw = gzip.compress(raw, mtime=0)
    return base64.b64encode(raw).decode("ascii")


def splice_programs2(
    template_path: Path, new_records: list[dict], output_path: Path
) -> Path:
    """Append ``new_records`` to the bundle's PROGRAMS2 array, leaving all else intact.

    The existing records are preserved verbatim (the new ones are inserted just before
    the array's closing bracket) and every other asset in the manifest is untouched, so
    the 81 committed briefs render exactly as before and only the additions are new.
    """
    html = Path(template_path).read_text(encoding="utf-8")
    match = _MANIFEST_RE.search(html)
    if not match:
        raise BriefBundleError("Bundle has no __bundler/manifest script.")
    manifest = json.loads(match.group(1))
    uuid = _find_programs2_uuid(manifest)

    js = _decode_asset(manifest[uuid]).decode("utf-8")
    close = js.rindex("]")
    additions = "".join(
        "," + json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        for record in new_records
    )
    new_js = js[:close] + additions + js[close:]
    _parse_programs2_array(new_js)  # fail loudly if the edit produced invalid JSON

    manifest[uuid] = {**manifest[uuid], "data": _reencode_asset(manifest[uuid], new_js)}
    new_manifest = json.dumps(manifest, separators=(",", ":"), ensure_ascii=False)
    new_html = html[: match.start(1)] + new_manifest + html[match.end(1) :]

    output = Path(output_path)
    output.write_text(new_html, encoding="utf-8")
    return output
