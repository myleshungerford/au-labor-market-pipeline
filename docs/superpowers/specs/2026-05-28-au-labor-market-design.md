# AU Undergraduate Program Labor Market Analysis — Design Spec

**Date:** 2026-05-28
**Owner:** Office of Institutional Research and Assessment (commissioned by the Provost)
**Status:** Approved for implementation planning

## 1. Purpose

Map every bachelor's-level major at American University (AU) to labor market outcomes
(wages, projected job growth, projected annual openings) using only public, official
government data sources. Output is an Excel workbook for use in official undergraduate
program reviews. The deliverable format will iterate; the durable asset is a clean,
re-runnable data pipeline that outputs to a spreadsheet.

## 2. Scope

- **In scope:** Bachelor's-degree programs (majors) at AU; national and Washington-Arlington-Alexandria
  MSA labor market data; state-level projections for DC/MD/VA as a metro-growth proxy.
- **Out of scope:** Graduate programs; certificates; presentation/visualization layer (later iteration);
  any non-public or PII data.

## 3. Fixed parameters

| Parameter | Value |
|---|---|
| AU IPEDS UnitID | `131159` |
| DC MSA (OEWS area code) | `47900` (Washington-Arlington-Alexandria, DC-VA-MD-WV) |
| CIP version | CIP 2020 (6-digit) |
| SOC version | SOC 2018 (6-digit, detailed) |
| Award level filter | `AWLEVEL = 5` (Bachelor's) |
| Major filter | `MAJORNUM = 1` (first major), `CTOTALT > 0` in latest year |
| States for regional projections | DC, MD, VA |

## 4. Key decisions (confirmed)

1. **Acquisition:** Automated HTTP download with caching to `raw/`. Re-runs reuse the cache.
   On download failure, the pipeline logs the exact expected filename + URL so a file can be
   placed manually in `raw/` and picked up on re-run (manual safety net).
2. **Completions source:** Raw IPEDS Completions complete-data file from NCES (latest available year).
   Not scipeds (only through 2023) and not the Urban Institute API.
3. **Major definition:** First-major bachelor's awards (`AWLEVEL=5`, `MAJORNUM=1`) with `CTOTALT > 0`
   in the most recent completions year.
4. **OEWS source:** The OEWS data-file zips (`oesm{YY}nat.zip` national, `oesm{YY}ma.zip` metro filtered
   to area `47900`) — **not** the `time.series/oe/` LABSTAT flat files. Same official source; the zip
   tables provide one clean row per SOC per area with median/mean/percentile wages, employment, and
   location quotient directly. (Changed from original starter prompt; confirmed.)
5. **Summary aggregation:** Employment-weighted **mean of each occupation's median wage**
   (a true weighted median of medians is impossible without microdata). Each summary row also carries
   min/max of occupational medians and occupation count to preserve the range. (Confirmed.)
6. **Governance:** All sources are public, aggregate, non-PII government data; no FERPA exposure.
   A one-paragraph governance note goes in the Methodology sheet in lieu of a full data-governance audit.
   (Confirmed.)
7. **Build scope:** Build the pipeline AND run it end-to-end on live data to produce a populated,
   spot-checked workbook in this session.

## 5. Architecture

Modular, staged pipeline. One module per source (acquire), transform modules, one Excel writer,
and a thin orchestrator. Each stage caches its output so re-runs skip finished work.

```
Review/
  raw/            # downloaded source files, untouched (gitignored)
  processed/      # cached intermediate outputs (parquet/csv) per stage
  output/         # final .xlsx
  logs/           # run logs
  src/
    config.py         # constants: UNITID, MSA, URLs, contact email, paths, vintage pins
    acquire/
      ipeds.py        # download + parse Completions; filter bachelor's first-majors
      crosswalk.py    # download + parse CIP2020->SOC2018 xlsx (many-to-many)
      oews.py         # download + parse national + DC-metro wage/employment zips
      projections.py  # download + parse national 10-yr projections
      state_proj.py   # download + parse Projections Central DC/MD/VA
    transform/
      mapping.py      # build AU CIP -> [SOC...] map; flag no-match CIPs
      join.py         # attach national/metro/state metrics to each AU-CIP-SOC row
      aggregate.py    # employment-weighted per-program summary rows
    excel_writer.py   # Summary / Detail / Crosswalk Reference / Methodology sheets
    run.py            # orchestrator: logging, cache checks, ordered stage calls
  requirements.txt
  README.md
  tests/
```

## 6. Data flow

```
IPEDS Completions
  -> AU bachelor's first-major CIP list (CIP, program name, awards count)
  -> CIP2020->SOC2018 crosswalk (many-to-many expansion)
  -> AU-CIP-to-SOC pairs  [+ flag CIPs with no SOC match, kept not dropped]
  -> JOIN:
       OEWS national (median/mean/pct wages, employment)
       OEWS metro 47900 (median/mean/pct wages, employment, location quotient, suppression flag)
       National projections (base/proj employment, numeric & % change, annual openings,
                             median wage, typical entry-level education)
       State projections DC/MD/VA (growth % where available)
  -> DETAIL table (one row per CIP x SOC, full metrics)
  -> AGGREGATE (employment-weighted)
  -> SUMMARY table (one row per CIP)
```

## 7. Data sources and parsing notes

| Source | URL (to verify at runtime) | Key fields |
|---|---|---|
| IPEDS Completions | NCES complete data files (latest `C{YYYY}_A`) | `UNITID`, `CIPCODE`, `AWLEVEL`, `MAJORNUM`, `CTOTALT` |
| CIP-SOC crosswalk | `nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx` | CIP code, CIP title, SOC code, SOC title |
| OEWS national | `bls.gov/oes` data zip `oesm{YY}nat.zip` | `OCC_CODE`, `O_GROUP`, `TOT_EMP`, `A_MEDIAN`, `A_MEAN`, `A_PCT10/25/75/90` |
| OEWS metro | `bls.gov/oes` data zip `oesm{YY}ma.zip` (filter `AREA=47900`) | as above + `LOC_QUOTIENT`; suppression markers `*` / `#` |
| National projections | BLS Employment Projections occupational table | SOC, base & proj employment, change #/%, annual openings, median wage, entry education |
| State projections | `projectionscentral.org` long-term export (filter DC/MD/VA) | state, SOC, base/proj employment, % change |

**Parsing rules:**
- OEWS and projections: keep only **detailed** SOC rows (`O_GROUP = 'detailed'`); drop major/broad/total rows.
- OEWS suppressed wage/employment values (`*`, `#`, blank) -> null + `metro_suppressed` / `national_suppressed` flag; never zero-fill.
- Crosswalk: a CIP may map to many SOCs and vice versa. Expand fully. Crosswalk rows with
  "No SOC match"/blank SOC -> the CIP is retained with `soc_match = FALSE`.
- All codes align on CIP 2020 / SOC 2018, so no cross-vintage code translation is needed.

## 8. Output workbook

- **Summary sheet** — one row per AU major: CIP, program name, awards count, occupation count,
  `soc_match` flag, employment-weighted mean of national median wages, min/max occupational median,
  employment-weighted national projected growth %, total national annual openings across associated
  occupations (summed; labeled as non-exclusive to the major — see limitation 9), metro
  employment-weighted median wage (where available), and a `metro_data_partial` flag.
- **Detail sheet** — one row per AU-major-to-occupation mapping with full national + metro + state metrics.
- **Crosswalk Reference sheet** — the full CIP-to-SOC mapping actually used.
- **Methodology sheet** — data sources, exact vintages, URLs, download dates, governance note,
  and the documented limitations (Section 10).

## 9. Error handling and QA

- Downloads use a BLS-compliant `User-Agent` containing a contact email, with `tenacity` retries.
  On final failure, log the exact expected filename + URL and continue/abort cleanly.
- **No silent drops:** assert input AU CIP count equals the count represented in Summary output.
- No-SOC-match CIPs appear in Summary with blank metrics and `soc_match = FALSE`.
- Suppressed metro/national estimates preserved as null with explicit flags.
- Spot-check harness prints summaries for Computer Science (`11.0701`), Economics (`45.0601`),
  and Political Science (`45.1001`) for sanity-checking against the BLS Occupational Outlook Handbook.

## 10. Documented limitations (carried into Methodology sheet)

1. The CIP-SOC crosswalk is expert-judgment-based, not derived from actual graduate employment outcomes.
2. Metro-area employment projections are not published by government sources; state-level DC/MD/VA
   projections are used as a proxy.
3. Some metro OEWS estimates are suppressed by BLS due to small sample size; shown as null, not zero.
4. The crosswalk is many-to-many, so summary statistics obscure the range of outcomes; the Detail sheet
   is the source of truth.
5. Employment-weighting can pull a program's summary toward large catch-all occupations (e.g., "General
   and Operations Managers") that map to many majors.
6. BLS projections assume no major structural disruptions and incorporate AI impacts conservatively.
7. OEWS covers wage-and-salary workers only (excludes the self-employed).
8. Data vintages are whatever is current at run time; exact vintage + download date is recorded per source.
9. Summed annual openings in the Summary sheet count openings across all occupations a major maps to;
   those occupations are not exclusive to that major, so the figure is an addressable-opportunity
   indicator, not openings attributable solely to the program.

## 11. Testing

Unit tests on small fixtures:
- crosswalk many-to-many expansion (1 CIP -> N SOC; N CIP -> 1 SOC),
- employment-weighted average math, including the all-suppressed -> null case,
- no-SOC-match flagging and no-silent-drop assertion.

Integration validation: full live fetch run end-to-end; eyeball the three spot-check programs.

## 12. Dependencies (requirements.txt)

`pandas`, `openpyxl`, `xlsxwriter`, `requests`, `tenacity`, `tqdm`, `pyarrow` (parquet cache).
Secrets (none required for these public sources) would use Windows Credential Manager via `keyring`
if a keyed API were added later; the current sources need no API key.

## 13. Open items to verify at runtime (not assumptions)

- Which OEWS vintage is live (May 2024 vs May 2025) and the exact zip filenames.
- Which national projections cycle is posted (2024-34 vs 2023-33) and the exact download URL.
- Latest IPEDS Completions year available and exact complete-data-file name.
- Current Projections Central long-term vintage and export format.
- Exact IPEDS Completions field names in the latest file (confirm `MAJORNUM`, `CTOTALT`, `AWLEVEL`).
