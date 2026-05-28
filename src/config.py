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
PROJECTIONS_URL = "https://www.bls.gov/emp/data/occupational-data.htm"  # resolve the .xlsx link at runtime
STATE_PROJECTIONS_URL = (
    "https://projectionscentral.org/longterm"  # resolve the export at runtime
)

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
