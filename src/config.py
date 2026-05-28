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
IPEDS_COMPLETIONS_FILE = (
    "C2023_A"  # Final 2023-24 collection; conferred Jul 2022-Jun 2023
)
OEWS_NATIONAL_ZIP = "oesm25nat.zip"  # May 2025 reference period
OEWS_METRO_ZIP = "oesm25ma.zip"

# --- Source URLs (confirm at runtime; acquisition fails loud if a file 404s) ---
CROSSWALK_URL = "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx"
IPEDS_COMPLETIONS_URL = "https://nces.ed.gov/ipeds/datacenter/data/C2023_A.zip"
OEWS_NATIONAL_URL = "https://www.bls.gov/oes/special-requests/oesm25nat.zip"
OEWS_METRO_URL = "https://www.bls.gov/oes/special-requests/oesm25ma.zip"
PROJECTIONS_URL = "https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx"  # EP occupation workbook; data on sheet "Table 1.2"
STATE_PROJECTIONS_URL = (
    "https://projectionscentral.org/longterm"  # human landing page (JS app)
)
# Projections Central bulk file endpoint returns JSON {"content": <900s presigned S3 CSV URL>}.
# Use ONLY this bulk path; the per-state paginated JSON endpoint silently drops ~100 rows/state.
STATE_PROJECTIONS_CSV_ENDPOINT = (
    "https://public.projectionscentral.org/projections/file/longterm/csv"
)
STATE_FIPS = {"DC": "11", "MD": "24", "VA": "51"}
# Guardrail (hard-fail if these shift): per-state row counts INCLUDING the 00-0000 total row,
# and the projection cycle. A mismatch means upstream vintage/coverage changed; stop and review.
STATE_EXPECTED_COUNTS = {"11": 442, "24": 749, "51": 741}
STATE_PROJECTION_VINTAGE = ("2022", "2032")

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
