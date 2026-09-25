"""
analytics.py — Performance metrics calculate karne wala module
Team-wise, Dialer-wise conversion, amounts, dates.
Revenue aur amount dono handle karta hai.
Duplicate sales ko 1 baar count karta hai (_is_primary_sale).

⚠️ Har function defensive hai — agar column nahi mila toh crash nahi hoga.
"""

import pandas as pd


def to_numeric_safe(series):
    """String ko number mein safely convert karo"""
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
        errors="coerce"
    )


def safe_round(value, decimals=2):
    """Value ko safely round karo"""
    try:
        if pd.isna(value):
            return 0
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return 0


def safe_sum(series):
    """Series ka safe sum"""
    if series is None or len(series) == 0:
        return 0
    numeric = to_numeric_safe(series)
    total = numeric.sum()
    if pd.isna(total):
        return 0
    return float(total)


def get_amount_column(df):
    """DataFrame mein amount ya revenue column dhoondo"""
    if df is None or len(df) == 0:
        return None
    if "amount" in df.columns:
        return "amount"
    if "revenue" in df.columns:
        return "revenue"
    return None


def get_primary_sales(df):
    """
    Sirf primary sales rows filter karo.
    Agar _is_primary_sale column nahi hai toh saari rows return karo.
    """
    if df is None or len(df) == 0:
        return df
    if "_is_primary_sale" in df.columns:
        return df[df["_is_primary_sale"] == True]
    return df


def has_column(df, col):
    """DataFrame mein column hai ya nahi"""
    return df is not None and len(df) > 0 and col in df.columns


# ─────────────── Team Performance ───────────────
def team_performance(sold_df, no_sale_df):
    """
    Team-wise performance.
    Sales count = sirf primary sales (duplicate remove)
    Calls count = saari calls
    """
    empty_result = pd.DataFrame(columns=["team", "calls", "sales", "conversion_pct", "amount"])
    
    # ─── Check: team column exist karta hai? ───
    sold_has_team = has_column(sold_df, "team")
    no_sale_has_team = has_column(no_sale_df, "team")
    
    if not sold_has_team and not no_sale_has_team:
        return empty_result
    
    # ─── Primary sales filter ───
    sold_primary = get_primary_sales(sold_df)
    
    # ─── Sold stats ───
    sold_stats = pd.DataFrame()
    if has_column(sold_primary, "team"):
        df = sold_primary.copy()
        amount_col = get_amount_column(df)
        if amount_col:
            df["_amount_num"] = to_numeric_safe(df[amount_col])
        else:
            df["_amount_num"] = 0
        
        sold_stats = df.groupby("team").agg(
            sales=("team", "count"),
            amount=("_amount_num", "sum"),
        ).reset_index()
    
    # ─── All sold calls ───
    all_sold_calls = pd.DataFrame()
    if has_column(sold_df, "team"):
        all_sold_calls = sold_df.groupby("team").size().reset_index(name="sold_calls")
    
    # ─── No-sale stats ───
    no_sale_stats = pd.DataFrame()
    if has_column(no_sale_df, "team"):
        no_sale_stats = no_sale_df.groupby("team").size().reset_index(name="no_sale_calls")
    
    # ─── All teams ───
    all_teams = set()
    for df in [sold_stats, all_sold_calls, no_sale_stats]:
        if len(df) > 0 and "team" in df.columns:
            all_teams.update(df["team"].dropna().tolist())
    
    if not all_teams:
        return empty_result
    
    result = pd.DataFrame({"team": list(all_teams)})
    
    # Merge (safe)
    for df in [sold_stats, all_sold_calls, no_sale_stats]:
        if len(df) > 0 and "team" in df.columns:
            result = result.merge(df, on="team", how="left")
    
    # Ensure columns exist
    for col in ["sales", "amount", "sold_calls", "no_sale_calls"]:
        if col not in result.columns:
            result[col] = 0
    
    result = result.fillna(0)
    
    # ─── Calculations ───
    result["calls"] = result["sold_calls"] + result["no_sale_calls"]
    result["sales"] = result["sales"].astype(int)
    result["calls"] = result["calls"].astype(int)
    
    result["conversion_pct"] = (
        result["sales"] / result["calls"] * 100
    ).fillna(0).round(2)
    
    result["amount"] = result["amount"].apply(lambda x: safe_round(x, 2))
    
    result = result[["team", "calls", "sales", "conversion_pct", "amount"]]
    result = result.sort_values("amount", ascending=False).reset_index(drop=True)
    
    return result


# ─────────────── Dialer Performance ───────────────
def dialer_performance(sold_df, no_sale_df):
    """Dialer-wise performance — same logic"""
    empty_result = pd.DataFrame(columns=["dialer", "calls", "sales", "conversion_pct", "amount"])
    
    sold_has_dialer = has_column(sold_df, "dialer")
    no_sale_has_dialer = has_column(no_sale_df, "dialer")
    
    if not sold_has_dialer and not no_sale_has_dialer:
        return empty_result
    
    sold_primary = get_primary_sales(sold_df)
    
    # Sold stats
    sold_stats = pd.DataFrame()
    if has_column(sold_primary, "dialer"):
        df = sold_primary.copy()
        amount_col = get_amount_column(df)
        if amount_col:
            df["_amount_num"] = to_numeric_safe(df[amount_col])
        else:
            df["_amount_num"] = 0
        
        sold_stats = df.groupby("dialer").agg(
            sales=("dialer", "count"),
            amount=("_amount_num", "sum"),
        ).reset_index()
    
    # All sold calls
    all_sold_calls = pd.DataFrame()
    if has_column(sold_df, "dialer"):
        all_sold_calls = sold_df.groupby("dialer").size().reset_index(name="sold_calls")
    
    # No-sale
    no_sale_stats = pd.DataFrame()
    if has_column(no_sale_df, "dialer"):
        no_sale_stats = no_sale_df.groupby("dialer").size().reset_index(name="no_sale_calls")
    
    # All dialers
    all_dialers = set()
    for df in [sold_stats, all_sold_calls, no_sale_stats]:
        if len(df) > 0 and "dialer" in df.columns:
            all_dialers.update(df["dialer"].dropna().tolist())
    
    if not all_dialers:
        return empty_result
    
    result = pd.DataFrame({"dialer": list(all_dialers)})
    
    for df in [sold_stats, all_sold_calls, no_sale_stats]:
        if len(df) > 0 and "dialer" in df.columns:
            result = result.merge(df, on="dialer", how="left")
    
    for col in ["sales", "amount", "sold_calls", "no_sale_calls"]:
        if col not in result.columns:
            result[col] = 0
    
    result = result.fillna(0)
    
    result["calls"] = result["sold_calls"] + result["no_sale_calls"]
    result["sales"] = result["sales"].astype(int)
    result["calls"] = result["calls"].astype(int)
    
    result["conversion_pct"] = (
        result["sales"] / result["calls"] * 100
    ).fillna(0).round(2)
    
    result["amount"] = result["amount"].apply(lambda x: safe_round(x, 2))
    
    result = result[["dialer", "calls", "sales", "conversion_pct", "amount"]]
    result = result.sort_values("amount", ascending=False).reset_index(drop=True)
    
    return result


# ─────────────── Overall Stats ───────────────
def overall_stats(sold_df, no_sale_df, orphan_df):
    """
    Overall summary — defensive.
    Sales count = sirf primary sales.
    """
    sold_primary = get_primary_sales(sold_df)
    
    sold_len = len(sold_df) if sold_df is not None else 0
    sold_primary_len = len(sold_primary) if sold_primary is not None else 0
    no_sale_len = len(no_sale_df) if no_sale_df is not None else 0
    orphan_len = len(orphan_df) if orphan_df is not None else 0
    
    total_calls = sold_len + no_sale_len
    total_sales = sold_primary_len
    conversion = (total_sales / total_calls * 100) if total_calls > 0 else 0
    
    # Amount sirf primary sales se
    total_amount = 0
    if sold_primary is not None and len(sold_primary) > 0:
        amount_col = get_amount_column(sold_primary)
        if amount_col:
            total_amount = safe_sum(sold_primary[amount_col])
    
    return {
        "total_calls": total_calls,
        "total_sales": total_sales,
        "total_sold_calls": sold_len,
        "total_no_sale": no_sale_len,
        "total_orphan": orphan_len,
        "conversion_pct": round(conversion, 2),
        "total_amount": safe_round(total_amount, 2),
    }