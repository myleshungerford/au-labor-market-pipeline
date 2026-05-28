# AU Labor Market Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a re-runnable Python pipeline that maps every AU bachelor's major (IPEDS UnitID 131159) to national + DC-metro labor market outcomes and writes a four-sheet Excel workbook.

**Architecture:** Modular staged pipeline. One module per source under `src/acquire/` (download + parse), transform modules under `src/transform/` (mapping, join, aggregate), one `src/excel_writer.py`, and a thin `src/run.py` orchestrator. Downloads cache to `raw/`; each parser is unit-tested against small fixtures built in-test; the live fetch is exercised only by the final integration run. Acquisition fails loud on a missing pinned file.

**Tech Stack:** Python 3.12, pandas, openpyxl, xlsxwriter, requests, tenacity, tqdm, pyarrow, pytest.

**Spec:** `docs/superpowers/specs/2026-05-28-au-labor-market-design.md`

---

## Data contracts (canonical column names used across all tasks)

Every module produces/consumes pandas DataFrames with these exact lowercase column names. Codes are normalized strings.

- **completions**: `cip` (str "11.0701"), `awards` (int)
- **crosswalk**: `cip` (str), `cip_title` (str), `soc` (str "15-1252"), `soc_title` (str)
- **oews_national**: `soc`, `tot_emp` (float|NA), `a_median`, `a_mean`, `a_pct10`, `a_pct25`, `a_pct75`, `a_pct90` (all float|NA), `national_suppressed` (bool)
- **oews_metro**: `soc`, `tot_emp`, `a_median`, `a_mean`, `a_pct10`, `a_pct25`, `a_pct75`, `a_pct90`, `loc_quotient` (float|NA), `metro_suppressed` (bool)
- **projections**: `soc`, `emp_base` (float), `emp_proj` (float), `change_num` (float), `change_pct` (float), `annual_openings` (float), `median_wage` (float|NA), `entry_education` (str)
- **state_proj**: `soc`, `dc_change_pct` (float|NA), `md_change_pct` (float|NA), `va_change_pct` (float|NA)
- **detail** (one row per CIP x SOC): `cip`, `program_name`, `awards`, `soc`, `soc_title`, `soc_match` (bool), `catch_all` (bool), `entry_education`, `nat_tot_emp`, `nat_median`, `nat_growth_pct`, `nat_annual_openings`, `metro_tot_emp`, `metro_median`, `loc_quotient`, `metro_suppressed`, `dc_change_pct`, `md_change_pct`, `va_change_pct`
- **summary** (one row per CIP): `cip`, `program_name`, `awards`, `occupation_count`, `soc_match`, `catch_all_present`, `metro_data_partial`, `wtd_median_wage_national`, `wtd_median_wage_national_excl_catchall`, `wtd_median_wage_bachelors_entry`, `occ_median_min`, `occ_median_max`, `wtd_growth_pct_national`, `total_annual_openings`, `wtd_metro_median_wage`

`program_name` = the CIP title from the crosswalk (the IPEDS Completions file carries no title).

---

## File structure

- `requirements.txt`: dependencies
- `src/__init__.py`, `src/acquire/__init__.py`, `src/transform/__init__.py`: package markers
- `src/config.py`: constants (UNITID, MSA code, URLs, contact email, paths, vintage pins, catch-all SOCs, bachelor's-plus education set)
- `src/codes.py`: `normalize_cip`, `normalize_soc`
- `src/acquire/downloader.py`: `download(url, dest, *, headers, force)` with retries + cache + fail-loud
- `src/acquire/crosswalk.py`: `parse_crosswalk(xlsx_path)`, `get_crosswalk()`
- `src/acquire/ipeds.py`: `parse_completions(csv_path)`, `get_completions()`
- `src/acquire/oews.py`: `parse_oews(xlsx_path, *, is_metro)`, `get_oews_national()`, `get_oews_metro()`
- `src/acquire/projections.py`: `parse_projections(path)`, `get_projections()`
- `src/acquire/state_proj.py`: `parse_state_projections(path)`, `get_state_projections()`
- `src/transform/mapping.py`: `build_mapping(completions, crosswalk)`
- `src/transform/join.py`: `build_detail(mapping, oews_nat, oews_metro, proj, state)`
- `src/transform/aggregate.py`: `employment_weighted_mean(values, weights)`, `build_summary(detail)`
- `src/excel_writer.py`: `write_workbook(summary, detail, crosswalk_used, methodology, out_path)`
- `src/run.py`: orchestrator
- `tests/`: one test module per source file

---

### Task 1: Project scaffold and config

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`, `src/acquire/__init__.py`, `src/transform/__init__.py` (all empty)
- Create: `src/config.py`
- Create: `tests/__init__.py` (empty)
- Test: `tests/test_config.py`

- [ ] **Step 1: Write `requirements.txt`**

```
pandas>=2.2
openpyxl>=3.1
xlsxwriter>=3.2
requests>=2.32
tenacity>=9.0
tqdm>=4.66
pyarrow>=16.0
pytest>=8.0
```

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
from src import config


def test_core_constants():
    assert config.AU_UNITID == 131159
    assert config.DC_MSA_CODE == "47900"
    assert config.BACHELORS_AWLEVEL == 5
    assert config.FIRST_MAJOR == 1


def test_paths_are_under_project_root():
    for p in (config.RAW_DIR, config.PROCESSED_DIR, config.OUTPUT_DIR, config.LOG_DIR):
        assert str(p).startswith(str(config.PROJECT_ROOT))


def test_catch_all_and_education_sets():
    assert "11-1021" in config.CATCH_ALL_SOCS  # General and Operations Managers
    assert "Bachelor's degree" in config.BACHELORS_PLUS_EDUCATION
    assert "Associate's degree" not in config.BACHELORS_PLUS_EDUCATION
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 4: Create the package files and `src/config.py`**

Create empty `src/__init__.py`, `src/acquire/__init__.py`, `src/transform/__init__.py`, `tests/__init__.py`.

`src/config.py`:
```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

for _d in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Institution / geography ---
AU_UNITID = 131159
DC_MSA_CODE = "47900"

# --- IPEDS completions filters ---
BACHELORS_AWLEVEL = 5
FIRST_MAJOR = 1

# --- Pinned data vintages (see spec section 3.1) ---
IPEDS_COMPLETIONS_FILE = "C2023_A"            # Final 2023-24 collection; conferred Jul 2022-Jun 2023
OEWS_NATIONAL_ZIP = "oesm25nat.zip"           # May 2025 reference period
OEWS_METRO_ZIP = "oesm25ma.zip"

# --- Source URLs (confirm at runtime; acquisition fails loud if a file 404s) ---
CROSSWALK_URL = "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx"
IPEDS_COMPLETIONS_URL = "https://nces.ed.gov/ipeds/datacenter/data/C2023_A.zip"
OEWS_NATIONAL_URL = "https://www.bls.gov/oes/special-requests/oesm25nat.zip"
OEWS_METRO_URL = "https://www.bls.gov/oes/special-requests/oesm25ma.zip"
PROJECTIONS_URL = "https://www.bls.gov/emp/data/occupational-data.htm"  # resolve the .xlsx link at runtime
STATE_PROJECTIONS_URL = "https://projectionscentral.org/longterm"        # resolve the export at runtime

# --- HTTP ---
# BLS requests a descriptive User-Agent with a contact email (policy, not auth).
CONTACT_EMAIL = "myles@american.edu"  # CONFIRM before first live run
USER_AGENT = f"American University OIRA program-review pipeline ({CONTACT_EMAIL})"

# --- Methodology / classification helpers ---
STATES = ("DC", "MD", "VA")
# Catch-all occupations distort employment-weighted summaries. Maintained list + a rule
# that any SOC whose title ends with "All Other" is also treated as catch-all (see join.py).
CATCH_ALL_SOCS = {"11-1021"}  # General and Operations Managers
BACHELORS_PLUS_EDUCATION = {
    "Bachelor's degree",
    "Master's degree",
    "Doctoral or professional degree",
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src tests
git commit -m "feat: project scaffold and config constants"
```

---

### Task 2: Download utility with cache and fail-loud

**Files:**
- Create: `src/acquire/downloader.py`
- Test: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing test**

`tests/test_downloader.py`:
```python
import pytest
from src.acquire import downloader


def test_cache_hit_returns_without_network(tmp_path):
    dest = tmp_path / "already.txt"
    dest.write_text("cached")
    # No network needed; existing file is returned as-is.
    result = downloader.download("http://example.invalid/x", dest)
    assert result == dest
    assert dest.read_text() == "cached"


def test_missing_file_raises_when_download_fails(tmp_path, monkeypatch):
    dest = tmp_path / "missing.bin"

    class FakeResp:
        status_code = 404
        def raise_for_status(self):
            raise downloader.requests.HTTPError("404")

    monkeypatch.setattr(downloader.requests, "get", lambda *a, **k: FakeResp())
    with pytest.raises(downloader.requests.HTTPError):
        downloader.download("http://example.invalid/missing", dest, retries=1)
    assert not dest.exists()  # never leave a partial file
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_downloader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.acquire.downloader'`

- [ ] **Step 3: Write the implementation**

`src/acquire/downloader.py`:
```python
import logging
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src import config

log = logging.getLogger(__name__)


def download(url: str, dest, *, headers: dict | None = None, force: bool = False, retries: int = 4) -> Path:
    """Download url to dest with caching and retries. Fails loud on non-2xx."""
    dest = Path(dest)
    if dest.exists() and not force:
        log.info("cache hit: %s", dest.name)
        return dest

    hdrs = {"User-Agent": config.USER_AGENT}
    if headers:
        hdrs.update(headers)

    @retry(stop=stop_after_attempt(retries), wait=wait_exponential(multiplier=1, max=30), reraise=True)
    def _fetch() -> bytes:
        log.info("downloading %s", url)
        resp = requests.get(url, headers=hdrs, timeout=120)
        resp.raise_for_status()
        return resp.content

    content = _fetch()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(content)
    tmp.replace(dest)  # atomic; no partial file on failure
    log.info("saved %s (%d bytes)", dest.name, len(content))
    return dest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_downloader.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acquire/downloader.py tests/test_downloader.py
git commit -m "feat: caching download utility with retries and fail-loud"
```

---

### Task 3: Code normalizers

**Files:**
- Create: `src/codes.py`
- Test: `tests/test_codes.py`

- [ ] **Step 1: Write the failing test**

`tests/test_codes.py`:
```python
import pandas as pd
from src.codes import normalize_cip, normalize_soc


def test_normalize_cip_pads_and_formats():
    assert normalize_cip("11.0701") == "11.0701"
    assert normalize_cip(11.0701) == "11.0701"
    assert normalize_cip("1.0") == "01.0000"     # leading zero + decimal padding
    assert normalize_cip("45.06") == "45.0600"


def test_normalize_cip_handles_missing():
    assert normalize_cip(None) is pd.NA or normalize_cip(None) != normalize_cip(None)


def test_normalize_soc_strips_and_uppercases():
    assert normalize_soc(" 15-1252 ") == "15-1252"
    assert normalize_soc("15-1252.00") == "15-1252"   # drop OEWS detailed suffix if present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_codes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.codes'`

- [ ] **Step 3: Write the implementation**

`src/codes.py`:
```python
import pandas as pd


def normalize_cip(value) -> str:
    """Return a CIP code as 'NN.NNNN'. NA-safe."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NA
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return pd.NA
    if "." not in s:
        s = s + ".0"
    left, right = s.split(".", 1)
    return f"{int(left):02d}.{right[:4].ljust(4, '0')}"


def normalize_soc(value) -> str:
    """Return a SOC code as 'NN-NNNN'. Drops a trailing '.00' detailed suffix. NA-safe."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NA
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return pd.NA
    if "." in s:
        s = s.split(".", 1)[0]
    return s.upper()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_codes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/codes.py tests/test_codes.py
git commit -m "feat: CIP and SOC code normalizers"
```

---

### Task 4: Crosswalk parser

**Files:**
- Create: `src/acquire/crosswalk.py`
- Test: `tests/test_crosswalk.py`

The crosswalk xlsx columns are `CIP2020Code`, `CIP2020Title`, `SOC2018Code`, `SOC2018Title`. Rows with no occupation use the literal SOC code `"No Match"` (or a blank). Header may sit below a title row; the parser locates the header row by looking for `CIP2020Code`.

- [ ] **Step 1: Write the failing test**

`tests/test_crosswalk.py`:
```python
import pandas as pd
from src.acquire.crosswalk import parse_crosswalk


def _make_fixture(path):
    # Two header padding rows above the real header, like the real file.
    rows = [
        ["Crosswalk title", None, None, None],
        [None, None, None, None],
        ["CIP2020Code", "CIP2020Title", "SOC2018Code", "SOC2018Title"],
        ["11.0701", "Computer Science.", "15-1252", "Software Developers"],
        ["11.0701", "Computer Science.", "15-1211", "Computer Systems Analysts"],
        ["45.1001", "Political Science.", "19-3094", "Political Scientists"],
        ["30.9999", "Other Multi/Interdisc.", "No Match", "No Match"],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_parse_expands_and_normalizes(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    assert set(df.columns) == {"cip", "cip_title", "soc", "soc_title"}
    cs = df[df["cip"] == "11.0701"]
    assert sorted(cs["soc"]) == ["15-1211", "15-1252"]


def test_no_match_rows_have_na_soc(tmp_path):
    f = tmp_path / "cw.xlsx"
    _make_fixture(f)
    df = parse_crosswalk(f)
    pol = df[df["cip"] == "30.9999"]
    assert len(pol) == 1
    assert pd.isna(pol.iloc[0]["soc"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_crosswalk.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/acquire/crosswalk.py`:
```python
import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_cip, normalize_soc

log = logging.getLogger(__name__)
_NO_MATCH = {"no match", "no soc match", "none", ""}


def parse_crosswalk(xlsx_path) -> pd.DataFrame:
    raw = pd.read_excel(xlsx_path, header=None, dtype=str)
    header_idx = raw.index[raw.eq("CIP2020Code").any(axis=1)]
    if len(header_idx) == 0:
        raise ValueError(f"CIP2020Code header not found in {xlsx_path}")
    h = header_idx[0]
    df = raw.iloc[h + 1:].copy()
    df.columns = raw.iloc[h].tolist()
    df = df.rename(columns={
        "CIP2020Code": "cip", "CIP2020Title": "cip_title",
        "SOC2018Code": "soc", "SOC2018Title": "soc_title",
    })[["cip", "cip_title", "soc", "soc_title"]]
    df = df.dropna(subset=["cip"])
    df["cip"] = df["cip"].map(normalize_cip)
    df["cip_title"] = df["cip_title"].astype(str).str.rstrip(".").str.strip()
    is_no_match = df["soc"].astype(str).str.strip().str.lower().isin(_NO_MATCH)
    df["soc"] = df["soc"].map(normalize_soc)
    df.loc[is_no_match, "soc"] = pd.NA
    df.loc[is_no_match, "soc_title"] = pd.NA
    return df.dropna(subset=["cip"]).reset_index(drop=True)


def get_crosswalk() -> pd.DataFrame:
    dest = config.RAW_DIR / "CIP2020_SOC2018_Crosswalk.xlsx"
    download(config.CROSSWALK_URL, dest)
    return parse_crosswalk(dest)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_crosswalk.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acquire/crosswalk.py tests/test_crosswalk.py
git commit -m "feat: CIP-SOC crosswalk parser with no-match handling"
```

---

### Task 5: IPEDS completions parser

**Files:**
- Create: `src/acquire/ipeds.py`
- Test: `tests/test_ipeds.py`

The completions CSV uses columns `UNITID`, `CIPCODE`, `MAJORNUM`, `AWLEVEL`, `CTOTALT`. CIPCODE `"99"` (and `"99.0000"`) are institution grand-total rows and must be dropped. Keep only bachelor's (`AWLEVEL=5`), first major (`MAJORNUM=1`), this institution, `CTOTALT>0`.

- [ ] **Step 1: Write the failing test**

`tests/test_ipeds.py`:
```python
import pandas as pd
from src.acquire.ipeds import parse_completions


def _fixture(path):
    pd.DataFrame([
        # unitid, cipcode, majornum, awlevel, ctotalt
        [131159, "11.0701", 1, 5, 42],   # keep: CS bachelor's first major
        [131159, "45.0601", 1, 5, 30],   # keep: Economics
        [131159, "11.0701", 2, 5, 5],    # drop: second major
        [131159, "45.1001", 1, 3, 10],   # drop: not bachelor's (awlevel 3)
        [131159, "99",      1, 5, 999],  # drop: grand total CIP
        [131159, "26.0101", 1, 5, 0],    # drop: zero awards
        [999999, "11.0701", 1, 5, 88],   # drop: other institution
    ], columns=["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"]).to_csv(path, index=False)


def test_parse_filters_to_au_bachelors_first_major(tmp_path):
    f = tmp_path / "c.csv"
    _fixture(f)
    df = parse_completions(f)
    assert set(df.columns) == {"cip", "awards"}
    assert sorted(df["cip"]) == ["11.0701", "45.0601"]
    assert int(df[df["cip"] == "11.0701"]["awards"].iloc[0]) == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ipeds.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/acquire/ipeds.py`:
```python
import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_cip

log = logging.getLogger(__name__)


def parse_completions(csv_path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"CIPCODE": str}, low_memory=False)
    df.columns = [c.upper() for c in df.columns]
    df = df[
        (df["UNITID"] == config.AU_UNITID)
        & (df["AWLEVEL"] == config.BACHELORS_AWLEVEL)
        & (df["MAJORNUM"] == config.FIRST_MAJOR)
        & (df["CTOTALT"] > 0)
    ].copy()
    df = df[~df["CIPCODE"].astype(str).str.startswith("99")]  # drop grand-total rows
    df["cip"] = df["CIPCODE"].map(normalize_cip)
    df = df.dropna(subset=["cip"])
    out = df.groupby("cip", as_index=False)["CTOTALT"].sum().rename(columns={"CTOTALT": "awards"})
    return out.reset_index(drop=True)


def get_completions() -> pd.DataFrame:
    dest = config.RAW_DIR / f"{config.IPEDS_COMPLETIONS_FILE}.zip"
    download(config.IPEDS_COMPLETIONS_URL, dest)
    with zipfile.ZipFile(dest) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"no CSV inside {dest.name}: {zf.namelist()}")
        # prefer the revised/final file if present
        name = sorted(names, key=lambda n: ("_rv" not in n.lower(), n))[0]
        log.info("reading %s from %s", name, dest.name)
        with zf.open(name) as fh:
            return parse_completions(io.BytesIO(fh.read()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ipeds.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/acquire/ipeds.py tests/test_ipeds.py
git commit -m "feat: IPEDS completions parser (AU bachelor's first majors)"
```

---

### Task 6: OEWS parser (national and metro)

**Files:**
- Create: `src/acquire/oews.py`
- Test: `tests/test_oews.py`

OEWS data files are xlsx with uppercase columns: `AREA`, `OCC_CODE`, `OCC_TITLE`, group column (`O_GROUP` or `OCC_GROUP`, value `"detailed"`), `TOT_EMP`, `A_MEAN`, `A_MEDIAN`, `A_PCT10/25/75/90`, and (metro only) `LOC_QUOTIENT`/`LOC Q`. Suppressed values appear as `"*"`, `"**"`, `"#"`, or blank and become NA. `metro_suppressed`/`national_suppressed` is true when the median wage is NA after conversion.

- [ ] **Step 1: Write the failing test**

`tests/test_oews.py`:
```python
import numpy as np
import pandas as pd
import pytest
from src.acquire.oews import parse_oews, _to_num, _resolve_group_col


def test_to_num_handles_suppression():
    assert _to_num("48,500") == 48500.0
    assert pd.isna(_to_num("*"))
    assert pd.isna(_to_num("#"))
    assert pd.isna(_to_num(""))
    assert _to_num("123456") == 123456.0


def test_resolve_group_col_accepts_either_name():
    assert _resolve_group_col(["AREA", "O_GROUP", "TOT_EMP"]) == "O_GROUP"
    assert _resolve_group_col(["AREA", "OCC_GROUP", "TOT_EMP"]) == "OCC_GROUP"
    with pytest.raises(ValueError):
        _resolve_group_col(["AREA", "TOT_EMP"])


def _national_fixture(path):
    pd.DataFrame([
        ["99", "15-1252", "Software Developers", "detailed", "1500000", "130000", "120000", "70000", "95000", "150000", "190000"],
        ["99", "15-0000", "Computer Occupations", "major", "5000000", "100000", "95000", "", "", "", ""],
        ["99", "19-3094", "Political Scientists", "detailed", "6000", "*", "*", "*", "*", "*", "*"],
    ], columns=["AREA", "OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP", "A_MEAN", "A_MEDIAN", "A_PCT10", "A_PCT25", "A_PCT75", "A_PCT90"]).to_excel(path, index=False)


def test_parse_national_keeps_detailed_and_flags_suppression(tmp_path):
    f = tmp_path / "nat.xlsx"
    _national_fixture(f)
    df = parse_oews(f, is_metro=False)
    assert set(df["soc"]) == {"15-1252", "19-3094"}  # major row dropped
    dev = df[df["soc"] == "15-1252"].iloc[0]
    assert dev["a_median"] == 120000.0
    assert dev["national_suppressed"] == False
    pol = df[df["soc"] == "19-3094"].iloc[0]
    assert pd.isna(pol["a_median"])
    assert pol["national_suppressed"] == True


def _metro_fixture(path):
    pd.DataFrame([
        ["47900", "15-1252", "Software Developers", "detailed", "60000", "140000", "135000", "80000", "105000", "160000", "200000", "1.8"],
        ["10180", "15-1252", "Software Developers", "detailed", "2000", "120000", "118000", "70000", "90000", "140000", "180000", "1.1"],
    ], columns=["AREA", "OCC_CODE", "OCC_TITLE", "OCC_GROUP", "TOT_EMP", "A_MEAN", "A_MEDIAN", "A_PCT10", "A_PCT25", "A_PCT75", "A_PCT90", "LOC_QUOTIENT"]).to_excel(path, index=False)


def test_parse_metro_filters_to_dc_msa(tmp_path):
    f = tmp_path / "ma.xlsx"
    _metro_fixture(f)
    df = parse_oews(f, is_metro=True)
    assert list(df["soc"]) == ["15-1252"]  # only AREA 47900
    row = df.iloc[0]
    assert row["loc_quotient"] == 1.8
    assert row["metro_suppressed"] == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_oews.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/acquire/oews.py`:
```python
import logging
import zipfile
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_soc

log = logging.getLogger(__name__)

_GROUP_NAMES = ("O_GROUP", "OCC_GROUP")
_LQ_NAMES = ("LOC_QUOTIENT", "LOC Q", "LOC_Q")
_PCTS = {"a_pct10": "A_PCT10", "a_pct25": "A_PCT25", "a_pct75": "A_PCT75", "a_pct90": "A_PCT90"}


def _to_num(value):
    if value is None:
        return pd.NA
    s = str(value).strip().replace(",", "")
    if s == "" or s in {"*", "**", "#", "##"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def _resolve_group_col(columns) -> str:
    for name in _GROUP_NAMES:
        if name in columns:
            return name
    raise ValueError(f"no OEWS group column ({_GROUP_NAMES}) in {list(columns)}")


def _resolve_lq_col(columns):
    for name in _LQ_NAMES:
        if name in columns:
            return name
    return None


def parse_oews(xlsx_path, *, is_metro: bool) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]
    group_col = _resolve_group_col(df.columns)
    required = ["AREA", "OCC_CODE", "TOT_EMP", "A_MEAN", "A_MEDIAN", *_PCTS.values()]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"OEWS file missing columns {missing}; header was {list(df.columns)}")

    df = df[df[group_col].astype(str).str.lower() == "detailed"].copy()
    if is_metro:
        df = df[df["AREA"].astype(str).str.strip() == config.DC_MSA_CODE].copy()

    out = pd.DataFrame()
    out["soc"] = df["OCC_CODE"].map(normalize_soc)
    out["tot_emp"] = df["TOT_EMP"].map(_to_num)
    out["a_median"] = df["A_MEDIAN"].map(_to_num)
    out["a_mean"] = df["A_MEAN"].map(_to_num)
    for dst, src in _PCTS.items():
        out[dst] = df[src].map(_to_num)

    flag = "metro_suppressed" if is_metro else "national_suppressed"
    out[flag] = out["a_median"].isna()
    if is_metro:
        lq = _resolve_lq_col(df.columns)
        out["loc_quotient"] = df[lq].map(_to_num) if lq else pd.NA
    return out.dropna(subset=["soc"]).drop_duplicates(subset=["soc"]).reset_index(drop=True)


def _read_first_xlsx_from_zip(zip_path) -> pd.DataFrame.__class__:
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
        if not names:
            raise ValueError(f"no spreadsheet in {zip_path}: {zf.namelist()}")
        target = config.RAW_DIR / Path(names[0]).name
        with zf.open(names[0]) as fh, open(target, "wb") as out:
            out.write(fh.read())
    return target


def get_oews_national() -> pd.DataFrame:
    z = config.RAW_DIR / config.OEWS_NATIONAL_ZIP
    download(config.OEWS_NATIONAL_URL, z)
    return parse_oews(_read_first_xlsx_from_zip(z), is_metro=False)


def get_oews_metro() -> pd.DataFrame:
    z = config.RAW_DIR / config.OEWS_METRO_ZIP
    download(config.OEWS_METRO_URL, z)
    return parse_oews(_read_first_xlsx_from_zip(z), is_metro=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_oews.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acquire/oews.py tests/test_oews.py
git commit -m "feat: OEWS national/metro parser with defensive columns and suppression flags"
```

---

### Task 7: National projections parser

**Files:**
- Create: `src/acquire/projections.py`
- Test: `tests/test_projections.py`

The EP occupational table columns vary by release; map defensively from a candidate-name list to the canonical schema. Confirm the real header at runtime (spec Section 13). Keep only detailed SOC rows (6-digit `NN-NNNN`, not ending in `0000`).

- [ ] **Step 1: Write the failing test**

`tests/test_projections.py`:
```python
import pandas as pd
from src.acquire.projections import parse_projections


def _fixture(path):
    pd.DataFrame({
        "2023 National Employment Matrix code": ["15-1252", "19-3094", "15-0000"],
        "2023 National Employment Matrix title": ["Software Developers", "Political Scientists", "Computer Occupations"],
        "Employment, 2024": ["1500.0", "6.0", "5000.0"],
        "Employment, 2034": ["1700.0", "6.3", "5200.0"],
        "Employment change, numeric, 2024-34": ["200.0", "0.3", "200.0"],
        "Employment change, percent, 2024-34": ["13.3", "5.0", "4.0"],
        "Occupational openings, 2024-34 annual average": ["150.0", "0.6", "400.0"],
        "Median annual wage, 2024(1)": ["120000", "130000", "100000"],
        "Typical entry-level education": ["Bachelor's degree", "Master's degree", "Bachelor's degree"],
    }).to_excel(path, index=False)


def test_parse_maps_columns_and_drops_aggregates(tmp_path):
    f = tmp_path / "proj.xlsx"
    _fixture(f)
    df = parse_projections(f)
    assert set(df.columns) == {
        "soc", "emp_base", "emp_proj", "change_num", "change_pct",
        "annual_openings", "median_wage", "entry_education",
    }
    assert set(df["soc"]) == {"15-1252", "19-3094"}  # 15-0000 aggregate dropped
    cs = df[df["soc"] == "15-1252"].iloc[0]
    assert cs["change_pct"] == 13.3
    assert cs["annual_openings"] == 150.0
    assert cs["entry_education"] == "Bachelor's degree"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_projections.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/acquire/projections.py`:
```python
import logging
from pathlib import Path

import pandas as pd

from src import config
from src.acquire.downloader import download
from src.codes import normalize_soc

log = logging.getLogger(__name__)

# canonical -> list of substrings to match (case-insensitive) in the real header
_COLMAP = {
    "soc": ["matrix code", "soc code", "occupation code"],
    "emp_base": ["employment, 2024", "employment 2024"],
    "emp_proj": ["employment, 2034", "employment 2034"],
    "change_num": ["change, numeric", "numeric change"],
    "change_pct": ["change, percent", "percent change"],
    "annual_openings": ["openings"],
    "median_wage": ["median annual wage", "median wage"],
    "entry_education": ["entry-level education", "entry level education"],
}


def _find(columns, needles):
    for col in columns:
        low = str(col).lower()
        if any(n in low for n in needles):
            return col
    return None


def _to_num(value):
    s = str(value).strip().replace(",", "").replace("$", "")
    if s in {"", "nan", "-"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def parse_projections(path) -> pd.DataFrame:
    raw = pd.read_excel(path, dtype=str)
    resolved = {canon: _find(raw.columns, needles) for canon, needles in _COLMAP.items()}
    missing = [k for k, v in resolved.items() if v is None]
    if missing:
        raise ValueError(f"projections file missing columns {missing}; header was {list(raw.columns)}")
    out = pd.DataFrame()
    out["soc"] = raw[resolved["soc"]].map(normalize_soc)
    for num_col in ("emp_base", "emp_proj", "change_num", "change_pct", "annual_openings", "median_wage"):
        out[num_col] = raw[resolved[num_col]].map(_to_num)
    out["entry_education"] = raw[resolved["entry_education"]].astype(str).str.strip()
    out = out.dropna(subset=["soc"])
    out = out[out["soc"].str.match(r"^\d{2}-\d{4}$") & ~out["soc"].str.endswith("0000")]
    return out.drop_duplicates(subset=["soc"]).reset_index(drop=True)


def get_projections() -> pd.DataFrame:
    # PROJECTIONS_URL is a landing page; resolve the .xlsx link at runtime then cache it.
    dest = config.RAW_DIR / "ep_occupation_2024_34.xlsx"
    if not dest.exists():
        raise FileNotFoundError(
            f"Place the BLS EP 2024-34 occupational data xlsx at {dest} "
            f"(resolve the download link from {config.PROJECTIONS_URL}). "
            "See spec Section 13."
        )
    return parse_projections(dest)
```

> **Runtime note for executor:** `get_projections()` deliberately fails loud with the exact expected path. During the integration run (Task 13), resolve the actual `.xlsx` link from the EP landing page, download it to `raw/ep_occupation_2024_34.xlsx` (using `downloader.download`), and adjust `_COLMAP` needles if the real header differs. This matches the spec's manual-fallback safety net.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_projections.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/acquire/projections.py tests/test_projections.py
git commit -m "feat: BLS employment projections parser with defensive column mapping"
```

---

### Task 8: State projections parser (Projections Central)

**Files:**
- Create: `src/acquire/state_proj.py`
- Test: `tests/test_state_proj.py`

Projections Central long-term export is long-form with `Area` (state name or abbrev), `Occupation Code` (SOC), and a percent-change column. Pivot to one row per SOC with `dc_change_pct`, `md_change_pct`, `va_change_pct`.

- [ ] **Step 1: Write the failing test**

`tests/test_state_proj.py`:
```python
import pandas as pd
from src.acquire.state_proj import parse_state_projections


def _fixture(path):
    pd.DataFrame({
        "Area": ["District of Columbia", "Maryland", "Virginia", "California"],
        "Occupation Code": ["15-1252", "15-1252", "15-1252", "15-1252"],
        "Percent Change": ["10.0", "12.5", "9.0", "20.0"],
    }).to_csv(path, index=False)


def test_parse_pivots_to_state_columns(tmp_path):
    f = tmp_path / "state.csv"
    _fixture(f)
    df = parse_state_projections(f)
    assert set(df.columns) == {"soc", "dc_change_pct", "md_change_pct", "va_change_pct"}
    row = df[df["soc"] == "15-1252"].iloc[0]
    assert row["dc_change_pct"] == 10.0
    assert row["md_change_pct"] == 12.5
    assert row["va_change_pct"] == 9.0  # California excluded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state_proj.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/acquire/state_proj.py`:
```python
import logging
from pathlib import Path

import pandas as pd

from src import config
from src.codes import normalize_soc

log = logging.getLogger(__name__)

_STATE_ALIASES = {
    "DC": {"dc", "district of columbia"},
    "MD": {"md", "maryland"},
    "VA": {"va", "virginia"},
}


def _state_key(area: str):
    a = str(area).strip().lower()
    for key, names in _STATE_ALIASES.items():
        if a in names:
            return key
    return None


def _find(columns, needles):
    for col in columns:
        if any(n in str(col).lower() for n in needles):
            return col
    return None


def _to_num(value):
    s = str(value).strip().replace("%", "").replace(",", "")
    if s in {"", "nan", "-"}:
        return pd.NA
    try:
        return float(s)
    except ValueError:
        return pd.NA


def parse_state_projections(path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str) if str(path).lower().endswith(".csv") else pd.read_excel(path, dtype=str)
    area_col = _find(raw.columns, ["area", "state"])
    soc_col = _find(raw.columns, ["occupation code", "soc"])
    pct_col = _find(raw.columns, ["percent change", "percent"])
    if not all([area_col, soc_col, pct_col]):
        raise ValueError(f"state projections missing columns; header was {list(raw.columns)}")
    raw = raw.copy()
    raw["state"] = raw[area_col].map(_state_key)
    raw = raw.dropna(subset=["state"])
    raw["soc"] = raw[soc_col].map(normalize_soc)
    raw["pct"] = raw[pct_col].map(_to_num)
    raw = raw.dropna(subset=["soc"])
    wide = raw.pivot_table(index="soc", columns="state", values="pct", aggfunc="first")
    wide = wide.rename(columns={"DC": "dc_change_pct", "MD": "md_change_pct", "VA": "va_change_pct"})
    for c in ("dc_change_pct", "md_change_pct", "va_change_pct"):
        if c not in wide.columns:
            wide[c] = pd.NA
    return wide.reset_index()[["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]]


def get_state_projections() -> pd.DataFrame:
    dest = config.RAW_DIR / "projections_central_longterm.csv"
    if not dest.exists():
        raise FileNotFoundError(
            f"Place the Projections Central 2022-32 long-term export at {dest} "
            f"(export from {config.STATE_PROJECTIONS_URL}). See spec Section 13."
        )
    return parse_state_projections(dest)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state_proj.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/acquire/state_proj.py tests/test_state_proj.py
git commit -m "feat: Projections Central state parser pivoting DC/MD/VA"
```

---

### Task 9: Build CIP-to-SOC mapping

**Files:**
- Create: `src/transform/mapping.py`
- Test: `tests/test_mapping.py`

Joins completions to the crosswalk. Every AU CIP is retained: CIPs with at least one SOC produce one row per SOC; CIPs with no SOC produce a single row with `soc_match=False` and NA `soc`. `program_name` comes from the crosswalk `cip_title`.

- [ ] **Step 1: Write the failing test**

`tests/test_mapping.py`:
```python
import pandas as pd
from src.transform.mapping import build_mapping


def test_mapping_expands_and_flags_no_match():
    completions = pd.DataFrame({"cip": ["11.0701", "30.9999"], "awards": [42, 7]})
    crosswalk = pd.DataFrame({
        "cip": ["11.0701", "11.0701", "30.9999"],
        "cip_title": ["Computer Science", "Computer Science", "Multi/Interdisciplinary"],
        "soc": ["15-1252", "15-1211", pd.NA],
        "soc_title": ["Software Developers", "Computer Systems Analysts", pd.NA],
    })
    m = build_mapping(completions, crosswalk)
    cs = m[m["cip"] == "11.0701"]
    assert sorted(cs["soc"]) == ["15-1211", "15-1252"]
    assert cs["soc_match"].all()
    assert (cs["program_name"] == "Computer Science").all()
    nomatch = m[m["cip"] == "30.9999"]
    assert len(nomatch) == 1
    assert nomatch.iloc[0]["soc_match"] == False
    assert pd.isna(nomatch.iloc[0]["soc"])


def test_no_au_program_is_dropped():
    completions = pd.DataFrame({"cip": ["11.0701", "99.9999"], "awards": [42, 1]})
    crosswalk = pd.DataFrame({"cip": ["11.0701"], "cip_title": ["CS"], "soc": ["15-1252"], "soc_title": ["Dev"]})
    m = build_mapping(completions, crosswalk)
    assert set(m["cip"]) == {"11.0701", "99.9999"}  # CIP absent from crosswalk still kept
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/transform/mapping.py`:
```python
import logging

import pandas as pd

log = logging.getLogger(__name__)


def build_mapping(completions: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    cw = crosswalk.copy()
    # CIP title lookup (first non-null title per CIP)
    titles = cw.dropna(subset=["cip_title"]).groupby("cip")["cip_title"].first()

    matched = cw.dropna(subset=["soc"])[["cip", "soc", "soc_title"]]
    rows = completions.merge(matched, on="cip", how="left")
    rows["soc_match"] = rows["soc"].notna()
    rows["program_name"] = rows["cip"].map(titles).fillna(rows["cip"])
    cols = ["cip", "program_name", "awards", "soc", "soc_title", "soc_match"]
    out = rows[cols].reset_index(drop=True)

    n_in = completions["cip"].nunique()
    n_out = out["cip"].nunique()
    assert n_in == n_out, f"CIP count changed in mapping: {n_in} -> {n_out}"
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mapping.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/transform/mapping.py tests/test_mapping.py
git commit -m "feat: CIP-to-SOC mapping with no-match retention and drop guard"
```

---

### Task 10: Join labor market metrics into the detail table

**Files:**
- Create: `src/transform/join.py`
- Test: `tests/test_join.py`

Left-joins (on `soc`) the national OEWS, metro OEWS, national projections, and state projections onto the mapping. Adds `catch_all` (config list OR title ends with "All Other"). Renames metrics to the `detail` contract. No-match rows keep NA metrics.

- [ ] **Step 1: Write the failing test**

`tests/test_join.py`:
```python
import pandas as pd
from src.transform.join import build_detail, _is_catch_all


def test_is_catch_all_rule():
    assert _is_catch_all("11-1021", "General and Operations Managers") is True   # config list
    assert _is_catch_all("13-1199", "Business Specialists, All Other") is True    # title rule
    assert _is_catch_all("15-1252", "Software Developers") is False


def test_build_detail_attaches_metrics_and_flags():
    mapping = pd.DataFrame({
        "cip": ["11.0701", "30.9999"], "program_name": ["CS", "Multi"],
        "awards": [42, 7], "soc": ["15-1252", pd.NA],
        "soc_title": ["Software Developers", pd.NA], "soc_match": [True, False],
    })
    nat = pd.DataFrame({"soc": ["15-1252"], "tot_emp": [1500000.0], "a_median": [120000.0],
                        "a_mean": [130000.0], "a_pct10": [70000.0], "a_pct25": [95000.0],
                        "a_pct75": [150000.0], "a_pct90": [190000.0], "national_suppressed": [False]})
    metro = pd.DataFrame({"soc": ["15-1252"], "tot_emp": [60000.0], "a_median": [135000.0],
                          "a_mean": [140000.0], "a_pct10": [80000.0], "a_pct25": [105000.0],
                          "a_pct75": [160000.0], "a_pct90": [200000.0], "loc_quotient": [1.8],
                          "metro_suppressed": [False]})
    proj = pd.DataFrame({"soc": ["15-1252"], "emp_base": [1500.0], "emp_proj": [1700.0],
                         "change_num": [200.0], "change_pct": [13.3], "annual_openings": [150.0],
                         "median_wage": [120000.0], "entry_education": ["Bachelor's degree"]})
    state = pd.DataFrame({"soc": ["15-1252"], "dc_change_pct": [10.0], "md_change_pct": [12.5], "va_change_pct": [9.0]})

    d = build_detail(mapping, nat, metro, proj, state)
    cs = d[d["cip"] == "11.0701"].iloc[0]
    assert cs["nat_median"] == 120000.0
    assert cs["nat_growth_pct"] == 13.3
    assert cs["nat_annual_openings"] == 150.0
    assert cs["metro_median"] == 135000.0
    assert cs["loc_quotient"] == 1.8
    assert cs["entry_education"] == "Bachelor's degree"
    assert cs["catch_all"] == False
    nm = d[d["cip"] == "30.9999"].iloc[0]
    assert pd.isna(nm["nat_median"])
    assert nm["soc_match"] == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_join.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/transform/join.py`:
```python
import logging

import pandas as pd

from src import config

log = logging.getLogger(__name__)


def _is_catch_all(soc, soc_title) -> bool:
    if soc in config.CATCH_ALL_SOCS:
        return True
    return str(soc_title).strip().lower().endswith("all other")


def build_detail(mapping, oews_nat, oews_metro, proj, state) -> pd.DataFrame:
    d = mapping.copy()

    nat = oews_nat.rename(columns={"tot_emp": "nat_tot_emp", "a_median": "nat_median"})
    d = d.merge(nat[["soc", "nat_tot_emp", "nat_median"]], on="soc", how="left")

    p = proj.rename(columns={"change_pct": "nat_growth_pct", "annual_openings": "nat_annual_openings"})
    d = d.merge(p[["soc", "nat_growth_pct", "nat_annual_openings", "entry_education"]], on="soc", how="left")

    m = oews_metro.rename(columns={"tot_emp": "metro_tot_emp", "a_median": "metro_median"})
    d = d.merge(m[["soc", "metro_tot_emp", "metro_median", "loc_quotient", "metro_suppressed"]], on="soc", how="left")

    d = d.merge(state[["soc", "dc_change_pct", "md_change_pct", "va_change_pct"]], on="soc", how="left")

    d["catch_all"] = [
        _is_catch_all(s, t) if pd.notna(s) else False
        for s, t in zip(d["soc"], d["soc_title"])
    ]
    d["entry_education"] = d["entry_education"].where(d["entry_education"].notna(), pd.NA)

    cols = ["cip", "program_name", "awards", "soc", "soc_title", "soc_match", "catch_all",
            "entry_education", "nat_tot_emp", "nat_median", "nat_growth_pct", "nat_annual_openings",
            "metro_tot_emp", "metro_median", "loc_quotient", "metro_suppressed",
            "dc_change_pct", "md_change_pct", "va_change_pct"]
    for c in cols:
        if c not in d.columns:
            d[c] = pd.NA
    return d[cols].reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_join.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/transform/join.py tests/test_join.py
git commit -m "feat: join OEWS/projections/state metrics into detail table"
```

---

### Task 11: Aggregate to per-program summary

**Files:**
- Create: `src/transform/aggregate.py`
- Test: `tests/test_aggregate.py`

Computes the employment-weighted summary per CIP. Weights are national employment (`nat_tot_emp`). Includes the all-occupation weighted wage, the catch-all-excluded weighted wage, and the bachelor's-plus-entry-education weighted wage. Metro weighted wage uses metro employment.

- [ ] **Step 1: Write the failing test**

`tests/test_aggregate.py`:
```python
import math
import pandas as pd
import pytest
from src.transform.aggregate import employment_weighted_mean, build_summary


def test_weighted_mean_basic():
    assert employment_weighted_mean([100.0, 200.0], [1.0, 3.0]) == 175.0


def test_weighted_mean_skips_na_pairs():
    assert employment_weighted_mean([100.0, None, 200.0], [1.0, 5.0, 3.0]) == 175.0


def test_weighted_mean_all_na_returns_na():
    assert pd.isna(employment_weighted_mean([None, None], [1.0, 2.0]))
    assert pd.isna(employment_weighted_mean([], []))


def _detail():
    return pd.DataFrame({
        "cip": ["11.0701", "11.0701", "30.9999"],
        "program_name": ["CS", "CS", "Multi"],
        "awards": [42, 42, 7],
        "soc": ["15-1252", "11-1021", pd.NA],
        "soc_title": ["Software Developers", "General and Operations Managers", pd.NA],
        "soc_match": [True, True, False],
        "catch_all": [False, True, False],
        "entry_education": ["Bachelor's degree", "Bachelor's degree", pd.NA],
        "nat_tot_emp": [1000.0, 3000.0, pd.NA],
        "nat_median": [120000.0, 100000.0, pd.NA],
        "nat_growth_pct": [13.0, 5.0, pd.NA],
        "nat_annual_openings": [150.0, 400.0, pd.NA],
        "metro_tot_emp": [600.0, 1400.0, pd.NA],
        "metro_median": [135000.0, 110000.0, pd.NA],
        "loc_quotient": [1.8, 1.2, pd.NA],
        "metro_suppressed": [False, False, pd.NA],
        "dc_change_pct": [10.0, 4.0, pd.NA],
        "md_change_pct": [12.0, 5.0, pd.NA],
        "va_change_pct": [9.0, 4.0, pd.NA],
    })


def test_summary_weighted_and_flags():
    s = build_summary(_detail())
    cs = s[s["cip"] == "11.0701"].iloc[0]
    # all-occupation weighted wage: (120000*1000 + 100000*3000)/4000 = 105000
    assert cs["wtd_median_wage_national"] == 105000.0
    # excluding catch-all (drop 11-1021): only 15-1252 -> 120000
    assert cs["wtd_median_wage_national_excl_catchall"] == 120000.0
    # bachelor's-entry: both are bachelor's -> same as all = 105000
    assert cs["wtd_median_wage_bachelors_entry"] == 105000.0
    assert cs["occupation_count"] == 2
    assert cs["occ_median_min"] == 100000.0
    assert cs["occ_median_max"] == 120000.0
    assert cs["total_annual_openings"] == 550.0
    assert cs["catch_all_present"] == True
    assert cs["soc_match"] == True
    # metro weighted wage: (135000*600 + 110000*1400)/2000 = 117500
    assert cs["wtd_metro_median_wage"] == 117500.0

    nm = s[s["cip"] == "30.9999"].iloc[0]
    assert nm["soc_match"] == False
    assert nm["occupation_count"] == 0
    assert pd.isna(nm["wtd_median_wage_national"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/transform/aggregate.py`:
```python
import logging

import pandas as pd

from src import config

log = logging.getLogger(__name__)


def employment_weighted_mean(values, weights):
    total_w = 0.0
    acc = 0.0
    for v, w in zip(values, weights):
        if v is None or w is None or pd.isna(v) or pd.isna(w):
            continue
        acc += float(v) * float(w)
        total_w += float(w)
    return acc / total_w if total_w > 0 else pd.NA


def _summarize_group(g: pd.DataFrame) -> pd.Series:
    matched = g[g["soc_match"] == True]  # noqa: E712
    excl = matched[matched["catch_all"] == False]  # noqa: E712
    bach = matched[matched["entry_education"].isin(config.BACHELORS_PLUS_EDUCATION)]
    return pd.Series({
        "program_name": g["program_name"].iloc[0],
        "awards": int(g["awards"].iloc[0]),
        "occupation_count": int(matched["soc"].nunique()),
        "soc_match": bool(matched.shape[0] > 0),
        "catch_all_present": bool((matched["catch_all"] == True).any()),  # noqa: E712
        "metro_data_partial": bool(matched["metro_suppressed"].fillna(True).any()) if matched.shape[0] else False,
        "wtd_median_wage_national": employment_weighted_mean(matched["nat_median"], matched["nat_tot_emp"]),
        "wtd_median_wage_national_excl_catchall": employment_weighted_mean(excl["nat_median"], excl["nat_tot_emp"]),
        "wtd_median_wage_bachelors_entry": employment_weighted_mean(bach["nat_median"], bach["nat_tot_emp"]),
        "occ_median_min": matched["nat_median"].min(),
        "occ_median_max": matched["nat_median"].max(),
        "wtd_growth_pct_national": employment_weighted_mean(matched["nat_growth_pct"], matched["nat_tot_emp"]),
        "total_annual_openings": matched["nat_annual_openings"].sum(min_count=1),
        "wtd_metro_median_wage": employment_weighted_mean(matched["metro_median"], matched["metro_tot_emp"]),
    })


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    summary = detail.groupby("cip", sort=True).apply(_summarize_group, include_groups=False).reset_index()
    ordered = ["cip", "program_name", "awards", "occupation_count", "soc_match",
               "catch_all_present", "metro_data_partial", "wtd_median_wage_national",
               "wtd_median_wage_national_excl_catchall", "wtd_median_wage_bachelors_entry",
               "occ_median_min", "occ_median_max", "wtd_growth_pct_national",
               "total_annual_openings", "wtd_metro_median_wage"]
    return summary[ordered]
```

> **Note:** `include_groups=False` requires pandas >= 2.2. If the installed pandas warns, that is acceptable; do not downgrade.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/transform/aggregate.py tests/test_aggregate.py
git commit -m "feat: employment-weighted per-program summary aggregation"
```

---

### Task 12: Excel writer

**Files:**
- Create: `src/excel_writer.py`
- Test: `tests/test_excel_writer.py`

Writes four sheets: Summary, Detail, Crosswalk Reference, Methodology. `methodology` is a list of `(label, value)` pairs assembled by `run.py`. Uses xlsxwriter via pandas `ExcelWriter`.

- [ ] **Step 1: Write the failing test**

`tests/test_excel_writer.py`:
```python
import pandas as pd
from openpyxl import load_workbook
from src.excel_writer import write_workbook


def test_workbook_has_all_sheets(tmp_path):
    summary = pd.DataFrame({"cip": ["11.0701"], "program_name": ["CS"], "awards": [42],
                            "wtd_median_wage_national": [105000.0]})
    detail = pd.DataFrame({"cip": ["11.0701"], "soc": ["15-1252"], "nat_median": [120000.0]})
    crosswalk_used = pd.DataFrame({"cip": ["11.0701"], "soc": ["15-1252"]})
    methodology = [("OEWS vintage", "May 2025 (released May 2026)"),
                   ("IPEDS", "C2023_A; conferred Jul 2022-Jun 2023")]
    out = tmp_path / "wb.xlsx"
    write_workbook(summary, detail, crosswalk_used, methodology, out)

    wb = load_workbook(out)
    assert wb.sheetnames == ["Summary", "Detail", "Crosswalk Reference", "Methodology"]
    assert wb["Summary"]["A1"].value == "cip"
    # methodology label/value present
    meth_vals = [c.value for row in wb["Methodology"].iter_rows() for c in row]
    assert "OEWS vintage" in meth_vals
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_excel_writer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/excel_writer.py`:
```python
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def write_workbook(summary, detail, crosswalk_used, methodology, out_path) -> Path:
    out_path = Path(out_path)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        detail.to_excel(xw, sheet_name="Detail", index=False)
        crosswalk_used.to_excel(xw, sheet_name="Crosswalk Reference", index=False)
        meth_df = pd.DataFrame(methodology, columns=["Item", "Detail"])
        meth_df.to_excel(xw, sheet_name="Methodology", index=False)

        wb = xw.book
        wrap = wb.add_format({"text_wrap": True, "valign": "top"})
        money = wb.add_format({"num_format": "$#,##0"})
        for name, frame in (("Summary", summary), ("Detail", detail),
                            ("Crosswalk Reference", crosswalk_used)):
            ws = xw.sheets[name]
            ws.freeze_panes(1, 0)
            for i, col in enumerate(frame.columns):
                width = min(max(len(str(col)) + 2, 12), 40)
                fmt = money if "wage" in col or "median" in col else None
                ws.set_column(i, i, width, fmt)
        xw.sheets["Methodology"].set_column(0, 0, 28)
        xw.sheets["Methodology"].set_column(1, 1, 90, wrap)
    log.info("wrote workbook %s", out_path)
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_excel_writer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/excel_writer.py tests/test_excel_writer.py
git commit -m "feat: four-sheet Excel workbook writer"
```

---

### Task 13: Orchestrator and integration run

**Files:**
- Create: `src/run.py`
- Create: `README.md`
- Test: manual integration run (no unit test; relies on prior unit tests)

`run.py` wires the stages, configures logging, caches each intermediate to `processed/` as parquet, asserts no AU program was dropped, prints the three spot-check programs, and writes the workbook. The Methodology list captures exact vintages, URLs, the cross-vintage disclosure, the IPEDS conferral-year note, the governance note, and the Section-10 limitations.

- [ ] **Step 1: Write `src/run.py`**

```python
import argparse
import datetime as dt
import logging

import pandas as pd

from src import config
from src.acquire import crosswalk, ipeds, oews, projections, state_proj
from src.transform import mapping, join, aggregate
from src.excel_writer import write_workbook

log = logging.getLogger("run")

SPOT_CHECK = {"11.0701": "Computer Science", "45.0601": "Economics", "45.1001": "Political Science"}

LIMITATIONS = [
    "CIP-SOC crosswalk is expert-judgment-based, not derived from actual graduate outcomes.",
    "Metro projections are not published; state DC/MD/VA 2022-32 used as proxy (national EP is 2024-34; base years differ).",
    "Some metro OEWS estimates are suppressed (shown as null, not zero).",
    "Crosswalk is many-to-many; summary obscures range. Detail sheet is the source of truth.",
    "Employment-weighting can pull summaries toward catch-all occupations; see catch_all flags and excl-catchall wage.",
    "BLS projections assume no major structural disruptions; AI impacts modeled conservatively.",
    "OEWS covers wage-and-salary workers only (excludes self-employed).",
    "Data vintages are pinned (spec 3.1); pipeline fails loud rather than substituting a release.",
    "Summed annual openings span all occupations a major maps to; addressable opportunity, not exclusive to the major.",
]


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(config.LOG_DIR / f"run_{dt.date.today()}.log")],
    )


def _cache(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_parquet(config.PROCESSED_DIR / f"{name}.parquet", index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore raw/ cache and re-download")
    args = ap.parse_args()
    _setup_logging()

    cw = _cache(crosswalk.get_crosswalk(), "crosswalk")
    comp = _cache(ipeds.get_completions(), "completions")
    nat = _cache(oews.get_oews_national(), "oews_national")
    metro = _cache(oews.get_oews_metro(), "oews_metro")
    proj = _cache(projections.get_projections(), "projections")
    state = _cache(state_proj.get_state_projections(), "state_projections")

    m = _cache(mapping.build_mapping(comp, cw), "mapping")
    detail = _cache(join.build_detail(m, nat, metro, proj, state), "detail")
    summary = _cache(aggregate.build_summary(detail), "summary")

    assert comp["cip"].nunique() == summary["cip"].nunique(), "AU program dropped between completions and summary"

    for cip, label in SPOT_CHECK.items():
        row = summary[summary["cip"] == cip]
        if row.empty:
            log.warning("spot-check %s (%s) not in AU completions this year", cip, label)
        else:
            r = row.iloc[0]
            log.info("SPOT %s %s: occ=%s wage_nat=%s growth=%s openings=%s",
                     cip, label, r["occupation_count"], r["wtd_median_wage_national"],
                     r["wtd_growth_pct_national"], r["total_annual_openings"])

    crosswalk_used = m[m["soc_match"]][["cip", "program_name", "soc", "soc_title"]].drop_duplicates()
    methodology = [
        ("Generated", dt.date.today().isoformat()),
        ("IPEDS Completions", f"{config.IPEDS_COMPLETIONS_FILE} (Final 2023-24 collection; degrees conferred Jul 2022-Jun 2023)"),
        ("CIP-SOC crosswalk", "CIP2020_SOC2018 (NCES)"),
        ("OEWS", "May 2025 reference period (released May 2026); national + DC MSA 47900"),
        ("National projections", "BLS Employment Projections 2024-34"),
        ("State projections", "Projections Central long-term 2022-32 (DC/MD/VA proxy; different base year from national)"),
        ("Governance", "All sources public, aggregate, non-PII government data; no FERPA exposure."),
        ("Summed openings", "Addressable opportunity across associated occupations, NOT exclusive to the major."),
    ]
    methodology += [(f"Limitation {i+1}", text) for i, text in enumerate(LIMITATIONS)]

    out = write_workbook(summary, detail, crosswalk_used, methodology,
                         config.OUTPUT_DIR / f"au_labor_market_{dt.date.today()}.xlsx")
    log.info("DONE: %d programs, %d detail rows -> %s", summary.shape[0], detail.shape[0], out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `README.md`**

```markdown
# AU Undergraduate Program Labor Market Analysis

Maps every AU bachelor's major (IPEDS UnitID 131159) to national and DC-metro labor
market outcomes using only public government data. See
`docs/superpowers/specs/2026-05-28-au-labor-market-design.md` for the full design.

## Setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```
python -m src.run            # uses cached files in raw/ when present
python -m src.run --force    # re-download everything
```
Two sources need a one-time manual placement in `raw/` (see spec Section 13):
`ep_occupation_2024_34.xlsx` (BLS EP 2024-34) and `projections_central_longterm.csv`.
The pipeline fails loud with the exact expected path if either is missing.

Output: `output/au_labor_market_<date>.xlsx` (Summary / Detail / Crosswalk Reference / Methodology).
```

- [ ] **Step 3: Run the full unit-test suite**

Run: `python -m pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 4: Integration run on live data**

Run: `python -m src.run`
Then, as needed per spec Section 13:
- If `get_projections()` / `get_state_projections()` raise FileNotFoundError, resolve the real download links, fetch the files into `raw/` at the named paths, and re-run.
- If an OEWS column assertion fails, inspect the logged header and adjust `oews._PCTS` / group resolution.
Expected: log shows the three spot-check programs with plausible wages (CS > ~$100k national), no "AU program dropped" assertion error, and `output/au_labor_market_<date>.xlsx` is created.

- [ ] **Step 5: Validate the workbook (dispatch a fresh verification agent)**

Per the user's self-verification rule, dispatch a fresh Opus agent to confirm observable conditions: the four sheets exist; Summary row count equals the AU bachelor's CIP count; no-match CIPs appear with blank metrics and `soc_match=FALSE`; suppressed metro rows are null not zero; CS/Econ/PoliSci wages are within sane ranges vs the BLS Occupational Outlook Handbook.

- [ ] **Step 6: Commit**

```bash
git add src/run.py README.md
git commit -m "feat: orchestrator, README, and end-to-end integration run"
```

---

## Self-review notes (completed during planning)

- **Spec coverage:** acquisition (Tasks 2,4-8), crosswalk many-to-many + no-match (Tasks 4,9), OEWS zip + metro filter + suppression + defensive columns (Task 6), national projections incl. entry education (Task 7), state DC/MD/VA proxy (Task 8), employment-weighted summary + min/max/count + excl-catchall + bachelor's-entry wage (Task 11), four-sheet workbook + Methodology with cross-vintage and conferral-year disclosure (Tasks 12,13), no-silent-drop assertion + spot checks (Tasks 9,13), fail-loud vintages (Tasks 2,7,8). All spec sections map to a task.
- **Placeholder scan:** every code step contains full code; the two manual-placement sources (projections, state) fail loud with exact paths rather than leaving a TODO.
- **Type consistency:** column names follow the Data Contracts section; function names (`build_mapping`, `build_detail`, `build_summary`, `parse_oews(is_metro=)`, `employment_weighted_mean`) are used identically across tasks and tests.
- **Known runtime adjustments (expected, not gaps):** exact EP/Projections Central download URLs and the OEWS group-column name are confirmed against real files during Task 13, per spec Section 13.
