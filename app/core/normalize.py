"""
normalize.py — Data normalisation utilities.

Cleans phone numbers, detects column names and coerces value types.
"""

import re
import pandas as pd


# ─────────────── Phone Number Cleaning ───────────────
def clean_phone(phone):
    """Normalise a phone number to a single standard form.

    Examples:
        "+92 300-1234567"  →  "03001234567"
        "92 300 1234567"   →  "03001234567"
        "0300-1234567"     →  "03001234567"
        "3001234567"       →  "03001234567"
    """
    if pd.isna(phone):
        return None

    s = str(phone).strip()
    digits = re.sub(r"\D", "", s)

    if not digits:
        return None

    # Normalise to the local national format
    if digits.startswith("92") and len(digits) >= 12:
        digits = "0" + digits[2:]
    elif len(digits) == 10 and digits.startswith("3"):
        digits = "0" + digits
    elif len(digits) == 11 and digits.startswith("03"):
        pass

    return digits


def clean_phone_column(df, col):
    """Clean every phone number in a column."""
    df[col] = df[col].apply(clean_phone)
    return df


# ─────────────── Column Detection ───────────────
def find_column(df, candidates):
    """Find the first column in the DataFrame matching any candidate name.

    Matching ignores letter case, spaces, underscores and dashes.
    """
    if not candidates:
        return None

    def norm(s):
        return re.sub(r"[\s_\-]+", "", str(s).lower().strip())

    normalized_df_cols = {norm(c): c for c in df.columns}

    for candidate in candidates:
        cand_norm = norm(candidate)
        if cand_norm in normalized_df_cols:
            return normalized_df_cols[cand_norm]

    return None


def detect_columns(df, config_columns):
    """Map the configured standard columns to the DataFrame's columns.

    Returns:
        dict: {standard_name: actual_column_name}
    """
    mapping = {}
    for standard_name, candidates in config_columns.items():
        found = find_column(df, candidates)
        if found:
            mapping[standard_name] = found
    return mapping


# ─────────────── Number Cleaning ───────────────
def clean_number(value):
    """Convert a value to a number.

    Handles inputs such as '7$', '$7', '1,234.50', 'PKR 500', 'N/A' and ''.
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    if not s or s.lower() in ("n/a", "na", "null", "none", "-", "--"):
        return None

    # Remove thousand separators
    s = s.replace(",", "")
    # Remove currency symbols and text, keeping only digits, dot and minus
    s = re.sub(r"[^\d.\-]", "", s)

    if not s or s in (".", "-", "-."):
        return None

    try:
        return float(s)
    except ValueError:
        return None


def clean_number_column(df, col):
    """Convert every value in a column to a number."""
    df[col] = df[col].apply(clean_number)
    return df