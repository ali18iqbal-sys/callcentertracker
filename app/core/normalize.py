"""
normalize.py — Data saaf karne wala module
Phone # clean karna, column names detect karna, types theek karna.
"""

import re
import pandas as pd


# ─────────────── Phone Number Cleaning ───────────────
def clean_phone(phone):
    """
    Phone # ko ek standard form mein laao.
    Examples:
        "+92 300-1234567"  →  "03001234567"
        "92 300 1234567"   →  "03001234567"
        "0300-1234567"     →  "03001234567"
        "3001234567"       →  "03001234567"
    """
    if pd.isna(phone):
        return None
    
    # String banao aur saare non-digit characters hatao
    s = str(phone).strip()
    digits = re.sub(r"\D", "", s)
    
    if not digits:
        return None
    
    # Pakistan format ke liye normalize karo
    # Agar +92 se shuru ho
    if digits.startswith("92") and len(digits) >= 12:
        digits = "0" + digits[2:]
    # Agar 3 se shuru ho (10 digits)
    elif len(digits) == 10 and digits.startswith("3"):
        digits = "0" + digits
    # Agar 03 se shuru ho (11 digits) — already sahi
    elif len(digits) == 11 and digits.startswith("03"):
        pass  # theek hai
    # Warna jaise hai waise chhor do
    
    return digits


def clean_phone_column(df, col):
    """Ek column ke saare phone numbers clean karo"""
    df[col] = df[col].apply(clean_phone)
    return df


# ─────────────── Column Detection ───────────────
def find_column(df, candidates):
    """
    DataFrame mein ek column dhoondo jo candidates mein se koi naam match kare.
    Case-insensitive, spaces/dashes ignore.
    
    Returns: Column ka actual naam, ya None
    """
    if not candidates:
        return None
    
    # Normalize karke compare karo
    def norm(s):
        return re.sub(r"[\s_\-]+", "", str(s).lower().strip())
    
    normalized_df_cols = {norm(c): c for c in df.columns}
    
    for candidate in candidates:
        cand_norm = norm(candidate)
        if cand_norm in normalized_df_cols:
            return normalized_df_cols[cand_norm]
    
    return None


def detect_columns(df, config_columns):
    """
    Config ke hisaab se DataFrame ke columns detect karo.
    
    Returns: dict {standard_name: actual_column_name}
    """
    mapping = {}
    for standard_name, candidates in config_columns.items():
        found = find_column(df, candidates)
        if found:
            mapping[standard_name] = found
    return mapping


# ─────────────── Number Cleaning ───────────────
def clean_number(value):
    """Text ko number mein convert karo. 'N/A', '', khali → None"""
    if pd.isna(value):
        return None
    
    s = str(value).strip()
    if not s or s.lower() in ("n/a", "na", "null", "none", "-", "--"):
        return None
    
    # Commas hatao (1,234 → 1234)
    s = s.replace(",", "")
    # Currency symbols hatao
    s = re.sub(r"[^\d.\-]", "", s)
    
    if not s:
        return None
    
    try:
        return float(s)
    except ValueError:
        return None


def clean_number_column(df, col):
    """Ek column ke saare values ko number banao"""
    df[col] = df[col].apply(clean_number)
    return df