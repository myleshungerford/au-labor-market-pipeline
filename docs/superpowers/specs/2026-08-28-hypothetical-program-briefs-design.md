# Adding Public Policy and Public Administration briefs (non-offered fields)

**Date:** 2026-08-28
**Status:** Implemented 2026-08-28 (surgical splice).
**Origin:** Illustrative briefs for two fields AU does not currently offer as undergraduate majors.

## Goal

Produce labor-market briefs for two fields AU does not offer as undergraduate
majors, **Public Policy** and **Public Administration**, as two separate briefs
folded into the existing full set (81 -> 83). To the reader they must be
ordinary program briefs with no "hypothetical" marking. A single maintainer-facing
line on the Methodology sheet records why they exist.

## Decisions

- **CIPs:** Public Administration -> `44.0401`; Public Policy Analysis -> `44.0501`.
  Both exist in the CIP2020-SOC2018 crosswalk with real SOC matches, so **no proxy
  CIP is needed**.
- **Display names:** exactly `Public Policy` and `Public Administration`, no degree suffix.
- **No reader-facing label.** Render as normal briefs.
- **Fold into the full set** -> 83 pages, alphabetical.
- **Methodology note** for a future maintainer only (not the reader).
- **Build approach:** surgical splice into the existing bundle (see below).

## Why this is clean

- The pipeline already carries CIPs with no AU completions
  ([run.py:76](../../../src/run.py) `active_program_cips`): they enter the CIP
  summary with zero awards. Adding these two CIPs is the *supported* path, not a workaround.
- The brief renders only CIP-level labor-market data (wages, growth, openings,
  occupation table). It shows **no school, degree, awards, or enrollment**
  (verified in the recovered component). A non-offered program is therefore not
  missing any brief content, and degree level does
  not change the output.
- Data check against the cached crosswalk/completions:
  - `44.0401` Public Administration -> 7 SOCs, management/government-heavy
    (Chief Executives, Legislators, Social & Community Service Managers, ...); 2
    catch-all manager codes are suppressed by the display rule, leaving 5 shown.
  - `44.0501` Public Policy Analysis -> 4 SOCs (Political Scientists, Legislators,
    Social Science Research Assistants, Poli-Sci Postsecondary Teachers).
  - Both confirmed **absent** from AU first-major bachelor's completions.
- Neither is a proxy and both are "ready," so the component shows **no draft stamp
  and no proxy box**.

## Current build chain (as-is)

1. `program_inventory.csv` + `program_cip_map.csv`
2. pipeline (`python -m src.run`) -> `au_program_onepager_data_<date>.xlsx` — **in repo, tested**
3. workbook -> `window.PROGRAMS2` JS — **generator NOT in repo** (bundle is stamped
   `Auto-generated from au_program_onepager_data 2026-06-03`)
4. `op2-brief.jsx` + React/ReactDOM/Babel + fonts + PROGRAMS2 -> one self-contained
   HTML — **bundler NOT in repo** (external tool; opaque base64+gzip manifest)
5. [program_briefs.py](../../../src/program_briefs.py) renders HTML -> full-set PDF
   -> per-program PDFs -> delivery ZIP — **in repo, tested**; page count must equal
   inventory row count.

Every part of steps 3-4 (the JSX component, the current PROGRAMS2 data, React,
ReactDOM, Babel, and all fonts) was recovered by decompressing the committed bundle.

## Approach

**Chosen: surgical, scripted splice into the existing bundle.**

Rationale: the 81 existing briefs were built 2026-06-03 from several live sources
(IPEDS, OEWS, Employment Projections, Projections Central, the CIP-SOC crosswalk).
A full rebuild re-derives all 81; if any source vintage or transform has drifted
since, the 81 numbers move and we own reconciling a drift that has nothing to do
with a two-program addendum. Freezing the 81 avoids that entirely.

Provenance confirmed for computing the two new records on the existing vintage:
config data-vintage pins and the transform modules are unchanged since the bundle
commit (HEAD); `raw/` holds the pinned source files; every `processed/` parquet is
dated 2026-06-03, matching the bundle stamp. The two new CIPs therefore compute from
the same sources and code as the 81, so the briefs' hardcoded footer
("OEWS May 2025; EP 2024-34") and shared "Prepared June 2026" masthead stay accurate
for them.

Rejected: full in-repo rebuild of steps 3-4. More durable, but its validation gate
(81-page parity) would trip on source/transform drift rather than on correctness,
i.e. the rabbit hole above. Revisit only if the briefs ever need a genuine full refresh.

## Work items

1. Add 2 rows to `program_inventory.csv` (ids `hp_ppol`, `hp_padm`; names
   `Public Policy`, `Public Administration`; school `SPA`, which is invisible on the
   brief) and 2 to `program_cip_map.csv` (`44.0501`, `44.0401`;
   `one_program_to_one_cip`; verified; notes marking them hypothetical). The `hp_` id
   is the only, reader-invisible, marker.
2. Run `python -m src.run` (no `--force`) -> refreshes the workbooks to include the
   two new CIPs from the cached 2026-06-03 sources. Does not touch the PDF bundle.
3. Add generator `src/brief_data.py`: workbook rows -> `PROGRAMS2` objects (recovered
   26-field + `occs[]` schema). Validate by reproducing a sample of the existing 81
   objects exactly against the recovered data, then emit the two new objects.
4. Add scripted splice (`src/brief_bundle.py`, named `brief_bundle_patch.py` in this
   plan): parse the template HTML's
   manifest, decompress the `PROGRAMS2` asset, append the two new objects (81 records
   untouched), recompress and re-embed, write the new self-contained HTML. Rename the
   template to a count-agnostic name and update the single `config` reference.
5. Run `python -m src.program_briefs` -> 83-page full set, per-program PDFs, delivery ZIP.
6. Add the maintainer note to `program_methodology()`.
7. Spot-check the two new briefs' numbers against the crosswalk SOCs and OEWS/EP rows.

## Verification (real path, not a proxy)

- **Generator:** sampled existing objects reproduced == recovered data, field for field.
- **Bundle integrity:** the 81 existing program records in the spliced bundle are
  byte-identical to the original; exactly two records added.
- **New briefs:** render as normal (no draft stamp, no proxy box); metric tiles and
  occupation table populated; every number traces to specific crosswalk SOCs and
  OEWS/EP source rows.
- **Ordering guard:** each rendered page's program name matches the alphabetically
  sorted inventory name at that position (the split labels pages by position, so a
  sort mismatch would silently mislabel).
- **Split:** full-set page count == inventory rows == 83; each per-program PDF is one
  page; ZIP holds 83.
- `pytest` green (existing brief/pipeline tests plus new generator tests).

## Risks / right-sizing

- The scripted splice mutates a 2.86 MB committed artifact. Mitigated by scripting it
  (repeatable, testable) rather than hand-editing, and by the byte-identical check on
  the 81 existing records.
- The generator only needs to be trusted for the two new records, but it is validated
  against known-good existing records so its field derivations are pinned to the real
  output, not assumed.
- All sources remain public, aggregate, non-PII government data; no new data-governance
  exposure.
- Partial reproducibility gained as a byproduct: generator + splice script are the
  reusable path for any future hypothetical-program addition, without committing to a
  full rebuild.
