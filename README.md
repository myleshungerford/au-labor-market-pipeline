# AU Undergraduate Program Labor Market Analysis

Maps every AU bachelor's major (IPEDS UnitID 131159) to national and DC-metro labor
market outcomes using only public government data. See
`docs/superpowers/specs/2026-05-28-au-labor-market-design.md` for the full design.

## Setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pip-audit && pip-audit
```

## Run
```
python -m src.run            # downloads + caches all sources to raw/, then builds the workbook
python -m src.run --force    # re-download everything, ignoring the raw/ cache
```
All six sources download automatically (IPEDS Completions, the CIP-SOC crosswalk, OEWS national
and DC-metro wages, BLS 2024-34 projections, and DC/MD/VA state projections). Downloads are cached
in `raw/` so re-runs are fast; `--force` refreshes them.

Outputs:
- `output/au_labor_market_<date>.xlsx` (CIP-level Summary / Detail / Crosswalk Reference / Methodology).
- `output/au_program_onepager_data_<date>.xlsx` (program-facing one-pager dataset keyed by `program_id`).

Populate `program_inventory.csv` and `program_cip_map.csv` with verified local program records to replace
the generated CIP placeholders in the program-facing workbook.

After reviewing the registrar active-program cleanup workbook, refresh those source CSVs with:
```
python -m src.active_program_sources --clean-workbook output/active_programs_cleaned_2026-05-29.xlsx
```

## Program labor-market briefs

`templates/AU_Program_Briefs_All_printable.html` is the print source for the
full brief set. It embeds every brief's data, so it is kept local and is not in this
repository (as of 2026-10-05); the brief-building tests skip without it. Keep corrections to the brief layout or copy in that file, then run:

```
python -m src.program_briefs
```

The command renders the full-set PDF, refreshes all one-page program PDFs in
`output/program-labor-market-briefs/`, and creates
`output/Program Labor-Market Briefs - Individual PDFs.zip` from that same render.
If the full-set PDF is corrected directly, use
`python -m src.program_briefs --split-only` to refresh the individual files and
the delivery ZIP without re-rendering the HTML. If an individual PDF is corrected
directly, use `python -m src.program_briefs --package-only` to refresh only the
delivery ZIP.

To add a program to the brief set, add its rows to `program_inventory.csv` and
`program_cip_map.csv`, run `python -m src.run` to refresh the one-pager workbook,
then run:

```
python -m src.build_briefs_bundle
```

This regenerates each program's data record from the workbook and splices any
program not already in the bundle into `window.PROGRAMS2`, leaving the existing
records and every other asset untouched. Run `python -m src.program_briefs`
afterward to re-render the PDFs. See
`docs/superpowers/specs/2026-08-28-hypothetical-program-briefs-design.md` for the
design and the data-provenance rationale.

Brief numbers are append-only: briefs 001-084 are frozen in their 2026-09-09
alphabetical order and each new program prints as the next number (page order is the
`PROGRAMS2` array order, so never re-sort it). An optional `brief_note` column in
`program_inventory.csv` prints one extra "How to read this" line on that program's
brief. Before adding a program, check its CIP's SOC rows in the crosswalk: many area and
ethnic studies CIPs map only to `25-1062`, which gives figures identical to existing
briefs. See `docs/superpowers/specs/2026-10-05-latinx-studies-brief-design.md`.

## Notes on data sources
- National + DC-metro figures (wages, employment, national growth and openings) are the
  load-bearing data, drawn from BLS OEWS and Employment Projections and IPEDS.
- The DC/MD/VA state growth columns are a best-effort regional proxy pulled from Projections
  Central's bulk file endpoint, which is an undocumented public endpoint and could change without
  notice. If it is unreachable the pipeline logs a warning and leaves the state columns blank; the
  national and metro figures are unaffected. The build hard-fails only if the source returns data
  whose per-state row counts or projection vintage no longer match the expected values (a guard
  against silently ingesting a shifted dataset).
- Exact data vintages and limitations are recorded on the workbook's Methodology sheet and in
  `docs/superpowers/specs/2026-05-28-au-labor-market-design.md`.
