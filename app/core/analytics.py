"""
analytics.py — Performance metrics calculate karne wala module
Team-wise, Dialer-wise conversion, amounts, dates.
"""

import pandas as pd


def to_numeric_safe(series):
    """String ko number mein safely convert karo"""
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )


def safe_round(value, decimals=2):
    """Value ko safely round karo — string ho toh 0"""
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


# ─────────────── Team Performance ───────────────
def team_performance(sold_df, no_sale_df):
    """
    Team-wise performance calculate karo.
    
    Returns: DataFrame with columns:
        team, calls, sales, conversion_pct, amount
    """
    if (sold_df is None or len(sold_df) == 0) and (no_sale_df is None or len(no_sale_df) == 0):
        return pd.DataFrame(columns=["team", "calls", "sales", "conversion_pct", "amount"])
    
    # ─── Sold stats ───
    sold_stats = pd.DataFrame()
    if sold_df is not None and len(sold_df) > 0 and "team" in sold_df.columns:
        df = sold_df.copy()
        if "amount" in df.columns:
            df["_amount_num"] = to_numeric_safe(df["amount"])
        else:
            df["_amount_num"] = 0
        
        sold_stats = df.groupby("team").agg(
            sales=("team", "count"),
            amount=("_amount_num", "sum"),
        ).reset_index()
    
    # ─── No-sale stats ───
    no_sale_stats = pd.DataFrame()
    if no_sale_df is not None and len(no_sale_df) > 0 and "team" in no_sale_df.columns:
        no_sale_stats = no_sale_df.groupby("team").agg(
            no_sale_calls=("team", "count"),
        ).reset_index()
    
    # ─── Merge ───
    if len(sold_stats) > 0 and len(no_sale_stats) > 0:
        result = pd.merge(sold_stats, no_sale_stats, on="team", how="outer").fillna(0)
    elif len(sold_stats) > 0:
        result = sold_stats.copy()
        result["no_sale_calls"] = 0
    elif len(no_sale_stats) > 0:
        result = no_sale_stats.copy()
        result["sales"] = 0
        result["amount"] = 0
    else:
        return pd.DataFrame(columns=["team", "calls", "sales", "conversion_pct", "amount"])
    
    # ─── Calculations ───
    result["calls"] = result["sales"] + result["no_sale_calls"]
    
    result["conversion_pct"] = (
        result["sales"] / result["calls"] * 100
    ).fillna(0).round(2)
    
    result["amount"] = result["amount"].apply(lambda x: safe_round(x, 2))
    
    result = result[["team", "calls", "sales", "conversion_pct", "amount"]]
    result = result.sort_values("amount", ascending=False).reset_index(drop=True)
    
    return result


# ─────────────── Dialer Performance ───────────────
def dialer_performance(sold_df, no_sale_df):
    """Dialer-wise performance"""
    if (sold_df is None or len(sold_df) == 0) and (no_sale_df is None or len(no_sale_df) == 0):
        return pd.DataFrame(columns=["dialer", "calls", "sales", "conversion_pct", "amount"])
    
    # ─── Sold stats ───
    sold_stats = pd.DataFrame()
    if sold_df is not None and len(sold_df) > 0 and "dialer" in sold_df.columns:
        df = sold_df.copy()
        if "amount" in df.columns:
            df["_amount_num"] = to_numeric_safe(df["amount"])
        else:
            df["_amount_num"] = 0
        
        sold_stats = df.groupby("dialer").agg(
            sales=("dialer", "count"),
            amount=("_amount_num", "sum"),
        ).reset_index()
    
    # ─── No-sale stats ───
    no_sale_stats = pd.DataFrame()
    if no_sale_df is not None and len(no_sale_df) > 0 and "dialer" in no_sale_df.columns:
        no_sale_stats = no_sale_df.groupby("dialer").agg(
            no_sale_calls=("dialer", "count"),
        ).reset_index()
    
    # ─── Merge ───
    if len(sold_stats) > 0 and len(no_sale_stats) > 0:
        result = pd.merge(sold_stats, no_sale_stats, on="dialer", how="outer").fillna(0)
    elif len(sold_stats) > 0:
        result = sold_stats.copy()
        result["no_sale_calls"] = 0
    elif len(no_sale_stats) > 0:
        result = no_sale_stats.copy()
        result["sales"] = 0
        result["amount"] = 0
    else:
        return pd.DataFrame(columns=["dialer", "calls", "sales", "conversion_pct", "amount"])
    
    result["calls"] = result["sales"] + result["no_sale_calls"]
    
    result["conversion_pct"] = (
        result["sales"] / result["calls"] * 100
    ).fillna(0).round(2)
    
    result["amount"] = result["amount"].apply(lambda x: safe_round(x, 2))
    
    result = result[["dialer", "calls", "sales", "conversion_pct", "amount"]]
    result = result.sort_values("amount", ascending=False).reset_index(drop=True)
    
    return result


# ─────────────── Overall Stats ───────────────
def overall_stats(sold_df, no_sale_df, orphan_df):
    """Overall summary — sab kuch safe"""
    
    sold_len = len(sold_df) if sold_df is not None else 0
    no_sale_len = len(no_sale_df) if no_sale_df is not None else 0
    orphan_len = len(orphan_df) if orphan_df is not None else 0
    
    total_calls = sold_len + no_sale_len
    total_sales = sold_len
    conversion = (total_sales / total_calls * 100) if total_calls > 0 else 0
    
    # Amount safely calculate karo
    total_amount = 0
    if sold_df is not None and len(sold_df) > 0 and "amount" in sold_df.columns:
        total_amount = safe_sum(sold_df["amount"])
    
    return {
        "total_calls": total_calls,
        "total_sales": total_sales,
        "total_no_sale": no_sale_len,
        "total_orphan": orphan_len,
        "conversion_pct": round(conversion, 2),
        "total_amount": safe_round(total_amount, 2),
    }