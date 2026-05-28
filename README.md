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

Output: `output/au_labor_market_<date>.xlsx` (Summary / Detail / Crosswalk Reference / Methodology).

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
