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

`templates/AU_Program_Briefs_All_81_printable.html` is the print source for the
full brief set. Keep corrections to the brief layout or copy in that file, then run:

```
python -m src.program_briefs
```

The command renders the full-set PDF and refreshes all one-page program PDFs in
`output/program-labor-market-briefs/` from that same render. If the full-set PDF
is corrected directly, use `python -m src.program_briefs --split-only` to refresh
the individual files without re-rendering the HTML.

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
