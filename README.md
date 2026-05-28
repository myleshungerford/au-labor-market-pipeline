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
python -m src.run
python -m src.run --force
```
Two sources need a one-time manual placement in `raw/` (see spec Section 13):
`ep_occupation_2024_34.xlsx` (BLS EP 2024-34) and `projections_central_longterm.csv`.
The pipeline fails loud with the exact expected path if either is missing.

Output: `output/au_labor_market_<date>.xlsx` (Summary / Detail / Crosswalk Reference / Methodology).
