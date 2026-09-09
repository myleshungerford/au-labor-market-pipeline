# Adding a Creative Writing brief (CIP 23.1302)

**Date:** 2026-09-09
**Status:** Implemented 2026-09-09 (surgical splice).
**Origin:** Request for labor-market data on two fields taught as tracks under the
Literature (BA): Creative Writing and Film/Cinema/Media Studies.

## Goal

Give Creative Writing its own labor-market brief, folded into the existing full set
(83 -> 84). Film/Cinema/Media Studies needed no new work: CIP `50.0601` is already
covered by the brief for `Communication: Film and Media Arts (BA)`, so that half of
the request was answered from the shipped set.

## Decisions

- **CIP:** Creative Writing -> `23.1302`. It exists in the CIP2020-SOC2018 crosswalk
  with four real SOC matches, so **no proxy CIP is needed**.
- **Display name:** exactly `Creative Writing`, no degree suffix. Considered and
  rejected: `Literature: Creative Writing (BA)`, which would have matched the naming
  of AU's other tracks in the set and sorted the brief next to
  `Literature: Cinema Studies (BA)`. The bare field name was chosen instead, matching
  the `Public Policy` / `Public Administration` precedent.
- **Sort position:** brief **029**, between `Computer Science (BS)` and `Dance (BA)`.
  Inserting alphabetically shifts the old 029-083 down one; `Communication: Film and
  Media Arts (BA)` stays at **023**.
- **Catch-all row left to the pipeline rule.** `23.1302` has only three non-catch-all
  occupations, below `ONE_PAGER_MIN_REAL_OCCUPATIONS` (5), so the display rule surfaces
  `25-1199 Postsecondary Teachers, All Other` rather than hiding it. No per-program
  override was added: the component already discloses it honestly (the row is tagged
  `catch-all`, the openings tile leads with the excl-catch-all figure and shows the
  all-mapped total underneath, and the wage tile carries an excl-catch-all subline).
  An override would have meant either moving a global threshold or adding a
  program-specific exception, both worse than the disclosed default.
- **No reader-facing "this is a track" label.** Render as an ordinary brief. A single
  maintainer-facing line on the Methodology sheet records what it is.
- **Build approach:** the same surgical splice used on 2026-08-28.

## Why this is clean

- The pipeline already carries CIPs with no AU completions
  ([run.py](../../../src/run.py) `active_program_cips`): they enter the CIP summary
  with zero awards. Creative Writing is a Literature (BA) track rather than a
  separately reported major, so `23.1302` has no AU first-major bachelor's
  completions and takes this supported path.
- The brief renders only CIP-level labor-market data and shows no school, degree,
  awards, or enrollment, so a track is not missing any brief content.
- Data check against the cached crosswalk (`23.1302` -> 4 SOCs):

  | SOC | Occupation | Nat. median | DC-metro median | Growth 2024-34 | Annual openings |
  |---|---|---|---|---|---|
  | 25-1199 | Postsecondary Teachers, All Other (catch-all) | $77,640 | $99,240 | +1.8% | 13,500 |
  | 27-3041 | Editors | $77,920 | $84,800 | +0.6% | 9,800 |
  | 25-1123 | English Language and Literature Teachers, Postsecondary | $78,760 | $82,080 | 0.0% | 5,100 |
  | 27-3043 | Writers and Authors | $76,910 | $108,460 | +3.6% | 13,400 |

  Weighted: `natWage` $77,799, `natWageExcl` $77,920, `metroWage` $92,533,
  `growth` +1.43%, `openings` 41,800, `openingsExcl` 28,300. Every figure was computed
  independently from `processed/*.parquet` before the build and matched the spliced
  record exactly.
- Not a proxy and `ready`, so the component shows **no draft stamp and no proxy box**
  (confirmed in the rendered PDF).

## Provenance (why the splice is still valid on this date)

The 2026-08-28 splice rested on the existing records computing from unchanged sources.
That held again here, and was checked rather than assumed:

- No `--force`. The five load-bearing sources (CIP-SOC crosswalk, IPEDS `C2023_A`,
  OEWS national and DC-metro `M2025`, EP `2024-34`) were all cache hits from `raw/`.
- Only the DC/MD/VA state proxy re-downloaded, because it is stored under a
  date-stamped filename. Its guardrails passed and a value-by-value diff against the
  previous pull showed **zero changes** across all 800 rows and all three columns. The
  state columns do not appear in a `PROGRAMS2` record and so cannot reach a brief
  regardless.
- All 83 pre-existing records regenerated from the fresh workbook **field-for-field
  identical** to the committed bundle, so nothing drifted.

## Build chain used

1. Add one row to `program_inventory.csv` (`trk_crwr`, `Creative Writing`, `CRWR`,
   school `CAS`, `active_status = track`) and one to `program_cip_map.csv`
   (`23.1302`, `one_program_to_one_cip`, verified). The `trk_` id is the only,
   reader-invisible, marker.
2. `python -m src.run` (no `--force`) -> refreshed workbooks, 76 CIP summary rows and
   84 program rows.
3. `python -m src.build_briefs_bundle` -> spliced one record into `window.PROGRAMS2`.
4. `python -m src.program_briefs` -> 84-page full set, 84 individual PDFs, delivery ZIP.
5. Maintainer note added to `program_methodology()`.

## Verification (real path, not a proxy)

- **Bundle integrity:** the 83 existing records in the spliced bundle are byte-identical
  to the pre-splice extract; exactly one record added.
- **Generator parity:** all 83 existing records regenerate from the new workbook exactly.
- **New brief:** renders with no draft stamp and no proxy box; all four metric tiles and
  the four-row occupation table populated; every number traces to specific crosswalk
  SOCs and OEWS/EP source rows.
- **Ordering guard:** all 84 rendered pages carry the expected alphabetically sorted
  inventory name at their position. This guard matters because the page shell sorts with
  JavaScript `localeCompare` while `program_briefs.load_program_names` sorts with Python
  `str.casefold`; the split labels pages by position only, so a divergence between the
  two collations would silently mislabel briefs without changing any count.
  *Note for a future run:* compare names with whitespace removed. `pypdf` drops the space
  at the point where a long title wraps in the header, so "African American and African
  Diaspora Studies (BA)" extracts as "African American andAfrican Diaspora Studies (BA)"
  and a naive substring check reports 12 false failures.
- **Split:** full-set page count == inventory rows == individual PDFs == ZIP entries == 84;
  each per-program PDF is one page with the filename's program name printed on it.
- `pytest` green (59 tests).

## Follow-ups left open (not done here)

- **The masthead reads "Prepared June 2026" on all 84 briefs.** It is a hardcoded
  constant in the bundle's JSX component asset (`const PREPARED = 'Prepared June 2026'`),
  not data-driven, so this brief inherits it. Defensible (every data vintage is unchanged
  since June 2026) but stale as a preparation date. Changing it means patching the
  component asset rather than the data asset. Deliberately left alone.
- `Literature: Cinema Studies (BA)` (brief 058) is mapped to `23.1401` General Literature
  and carries the cleanup flag `No exact master row; verify display name`. That name looks
  like a track name standing in for the parent Literature (BA). Unresolved and unrelated
  to this change, but adjacent to it.

## Risks / right-sizing

- The splice mutates a 2.86 MB committed artifact. Mitigated by scripting it, by the
  byte-identical check on the existing records, and by a pre-run backup.
- Adding a brief renumbers everything after the insertion point (old 029-083 -> 030-084).
  Filenames are the only place these numbers live; nothing external cites them.
- `tests/test_brief_bundle.py` previously asserted a literal record count, which broke on
  every addition. It now asserts the real invariant (one bundle record per inventory row),
  so the next addition does not need to edit it.
- All sources remain public, aggregate, non-PII government data; no new data-governance
  exposure.
