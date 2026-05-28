# AU Undergraduate Program Labor Market Analysis: Design Spec

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

### 3.1 Pinned data vintages (verified current as of 2026-05-28)

The pipeline pins these exact vintages in `config.py`. If an expected file 404s, the stage
**aborts loudly** and does NOT silently fall back to a prior year. Vintages are revisited only
by a deliberate config change.

| Source | Pinned vintage | Expected file | Notes |
|---|---|---|---|
| IPEDS Completions | **Final 2023-24 collection** | `C2023_A` | Reports degrees conferred July 2022 to June 2023 (award year 2022-23). Final (revised) chosen over Provisional 2024-25 for defensibility in an official, public review. |
| CIP-SOC crosswalk | CIP2020 / SOC2018 | `CIP2020_SOC2018_Crosswalk.xlsx` | Current crosswalk; URL verified live. |
| OEWS national | **May 2025** | `oesm25nat.zip` | Reference period May 2025; released May 2026 (USDL-26-0725). |
| OEWS metro | **May 2025** | `oesm25ma.zip` | All metros; filter `AREA == 47900` in code. |
| National projections | **2024-34** | BLS EP occupational data table | Released 2025-08-28. |
| State projections | **2022-32** | Projections Central long-term export | Newer cycle not yet published; vintage differs from national EP (see limitation 2 + 10). |

## 4. Key decisions (confirmed)

1. **Acquisition:** Automated HTTP download with caching to `raw/`. Re-runs reuse the cache.
   On download failure, the pipeline logs the exact expected filename + URL so a file can be
   placed manually in `raw/` and picked up on re-run (manual safety net).
2. **Completions source:** Raw IPEDS Completions complete-data file from NCES, **Final 2023-24 (`C2023_A`)**.
   Final chosen over Provisional 2024-25 for defensibility. Not scipeds (only through 2023) and not the Urban Institute API.
3. **Major definition:** First-major bachelor's awards (`AWLEVEL=5`, `MAJORNUM=1`) with `CTOTALT > 0`
   in the pinned completions year (Final 2023-24).
4. **OEWS source:** The OEWS data-file zips (`oesm25nat.zip` national, `oesm25ma.zip` metro filtered
   to area `47900`), **not** the `time.series/oe/` LABSTAT flat files. Same official source; the zip
   tables provide one clean row per SOC per area with median/mean/percentile wages, employment, and
   location quotient directly. (Changed from original starter prompt; confirmed.)
5. **Summary aggregation:** Employment-weighted **mean of each occupation's median wage**
   (a true weighted median of medians is impossible without microdata). The Summary header uses the
   verbatim label "employment-weighted mean of occupational median wages" so it is not misread as a
   true median. Each summary row also carries min/max of occupational medians and occupation count to
   preserve the range. (Confirmed.)
6. **Two wage figures:** Each program gets the all-occupation weighted wage **and** a second
   weighted wage restricted to associated SOCs whose BLS *typical entry-level education* is bachelor's
   or higher, answering "does this wage reflect degree-level jobs?" Both are clearly labeled. (Confirmed.)
7. **Governance:** All sources are public, aggregate, non-PII government data; no FERPA exposure.
   A one-paragraph governance note goes in the Methodology sheet in lieu of a full data-governance audit.
   (Confirmed.)
8. **Fail loud on vintage:** Acquisition aborts with a clear error if a pinned file (Section 3.1) is not
   found; no silent fallback to an earlier release.
9. **Build scope:** Build the pipeline AND run it end-to-end on live data to produce a populated,
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

| Source | Pinned file / URL | Key fields |
|---|---|---|
| IPEDS Completions | NCES complete data file `C2023_A` (Final 2023-24 collection; degrees conferred July 2022 to June 2023) | `UNITID`, `CIPCODE`, `AWLEVEL`, `MAJORNUM`, `CTOTALT` |
| CIP-SOC crosswalk | `nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx` (verified live) | CIP code, CIP title, SOC code, SOC title |
| OEWS national | `bls.gov/oes` data zip `oesm25nat.zip` (May 2025) | `OCC_CODE`, group col, `TOT_EMP`, `A_MEDIAN`, `A_MEAN`, `A_PCT10/25/75/90` |
| OEWS metro | `bls.gov/oes` data zip `oesm25ma.zip` (filter `AREA=47900`) | as above + `LOC_QUOTIENT`; suppression markers `*` / `#` |
| National projections | BLS Employment Projections 2024-34 occupational table | SOC, base & proj employment, change #/%, annual openings, median wage, entry education |
| State projections | `projectionscentral.org` long-term export, 2022-32 (filter DC/MD/VA) | state, SOC, base/proj employment, % change |

**Parsing rules:**
- OEWS and projections: keep only **detailed** SOC rows; drop major/broad/total rows. The group column
  name varies by vintage (`O_GROUP` vs `OCC_GROUP`), so resolve it defensively and assert expected
  columns exist after read, failing loud with the actual header list if not.
- OEWS suppressed wage/employment values (`*`, `#`, blank) -> null + `metro_suppressed` / `national_suppressed` flag; never zero-fill. Confirm the exact suppression markers against the real May 2025 file at runtime.
- Crosswalk: a CIP may map to many SOCs and vice versa. Expand fully. Crosswalk rows with
  "No SOC match"/blank SOC -> the CIP is retained with `soc_match = FALSE`.
- All codes align on CIP 2020 / SOC 2018, so no cross-vintage code translation is needed.

## 8. Output workbook

- **Summary sheet**, one row per AU major: CIP, program name, awards count, occupation count,
  `soc_match` flag, employment-weighted mean of occupational median wages (national), a second
  employment-weighted wage restricted to bachelor's-or-higher entry-education SOCs, min/max
  occupational median, employment-weighted national projected growth % (base year 2024-34), total
  national annual openings across associated occupations (summed; the caveat "addressable opportunity,
  not exclusive to this major, see limitation 9" appears on the sheet itself), metro employment-weighted
  median wage (where available), a `metro_data_partial` flag, and a `catch_all_present` flag indicating
  whether any associated SOC is a broad catch-all occupation (see below). A companion column or
  toggle shows the weighted wage with catch-all SOCs excluded.
- **State growth columns** never sit unlabeled beside national: any state (DC/MD/VA) growth % is shown
  in its own labeled `2022-32` column, distinct from the national `2024-34` growth column.
- **Catch-all flagging:** SOC rows known to be broad catch-alls (e.g., "General and Operations Managers",
  codes ending in residual patterns) are flagged via a small maintained list so Summary can be read
  with and without them; the flag also appears per row on the Detail sheet.
- **Detail sheet**, one row per AU-major-to-occupation mapping with full national + metro + state metrics,
  the per-SOC typical entry-level education, and the catch-all flag.
- **Crosswalk Reference sheet**, the full CIP-to-SOC mapping actually used.
- **Methodology sheet**, data sources, exact vintages, URLs, download dates, governance note,
  the cross-vintage disclosure (national EP 2024-34 vs state 2022-32 vs OEWS May 2025), the IPEDS
  conferral-year clarification (the 2023-24 collection reports degrees conferred July 2022 to June 2023),
  and the documented limitations (Section 10). Completions counts on the Summary/Detail sheets are
  labeled by conferral year, not collection year.

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
   projections are used as a proxy. The state proxy is the 2022-32 cycle while national projections
   are 2024-34, so the two have different base years and must never be compared without that label.
3. Some metro OEWS estimates are suppressed by BLS due to small sample size; shown as null, not zero.
4. The crosswalk is many-to-many, so summary statistics obscure the range of outcomes; the Detail sheet
   is the source of truth.
5. Employment-weighting can pull a program's summary toward large catch-all occupations (e.g., "General
   and Operations Managers") that map to many majors. Mitigated by the `catch_all_present` flag and a
   weighted-wage variant that excludes catch-all SOCs (Section 8), so the reader can see both.
6. BLS projections assume no major structural disruptions and incorporate AI impacts conservatively.
7. OEWS covers wage-and-salary workers only (excludes the self-employed).
8. Data vintages are pinned (Section 3.1) and recorded with download date per source; the pipeline fails
   loud rather than silently substituting a different release.
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

## 13. Open items to confirm at runtime (against the real files)

Vintages and the crosswalk URL were verified during design review (Section 3.1). What still must be
confirmed when the files are actually downloaded:

- The OEWS group column name in the May 2025 files (`O_GROUP` vs `OCC_GROUP`) and the exact suppression
  markers used; resolve defensively and assert columns exist.
- The exact download URL and column layout of the BLS EP 2024-34 occupational data table.
- The Projections Central 2022-32 long-term export format and column names for DC/MD/VA.
- That the pinned files (`C2023_A`, `oesm25nat.zip`, `oesm25ma.zip`) download successfully; abort loud if not.
- The IPEDS Completions field names in `C2023_A` (`MAJORNUM`, `CTOTALT`, `AWLEVEL`); the standard
  values were confirmed in review but should be asserted against the real header.

## 14. As-built notes (resolved during integration, 2026-05-28)

All six sources download automatically; none require manual file placement. The Section 13 items
were resolved against the real files as follows:

- **Crosswalk:** the NCES workbook has multiple sheets. The parser reads the `CIP-SOC` sheet (matched
  pairs) plus `Unmatched CIP Codes` (SOC `99-9999` / "NO MATCH" treated as no-match).
- **OEWS:** group column is `O_GROUP`; suppression markers `*`/`#`/blank become null. The national zip
  bundles a 4-digit aggregate file, so the detailed file is selected by the token `national`; the metro
  zip bundles BOS/MSA files, so the `MSA` member is selected and filtered to area `47900`.
- **National projections:** the file is `bls.gov/emp/ind-occ-matrix/occupation.xlsx`, sheet `Table 1.2`,
  with a title row above the header. Detailed rows are kept by `Occupation type == "Line item"`.
  Employment and openings are reported in thousands and converted to actual counts.
- **State projections:** automated via the Projections Central bulk file endpoint
  (`public.projectionscentral.org/projections/file/longterm/csv`, which returns a short-lived presigned
  CSV URL covering all states, 2022-32). The pipeline filters DC/MD/VA, archives each pull date-stamped,
  and hard-fails if per-state row counts (442/749/741) or the 2022-32 vintage shift. It degrades to blank
  state columns only if the (undocumented) endpoint is unreachable. The per-state paginated JSON endpoint
  is deliberately avoided: it silently drops about 100 occupations per state.
- **IPEDS:** `UNITID`, `CIPCODE`, `AWLEVEL`, `MAJORNUM`, `CTOTALT` confirmed in `C2023_A`.
