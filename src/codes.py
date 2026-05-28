import pandas as pd


def normalize_cip(value):
    """Return a CIP code as 'NN.NNNN' string, or pd.NA if missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NA
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return pd.NA
    if "." not in s:
        s = s + ".0"
    left, right = s.split(".", 1)
    return f"{int(left):02d}.{right[:4].ljust(4, '0')}"


def normalize_soc(value):
    """Return a SOC code as 'NN-NNNN' string (drops a trailing '.00' suffix), or pd.NA if missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NA
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return pd.NA
    if "." in s:
        s = s.split(".", 1)[0]
    return s.upper()
