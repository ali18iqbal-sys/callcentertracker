"""
matcher.py — Client aur Call Center data ko match karne wala module.
Phone # par match karta hai aur 3 categories banata hai:
    - SOLD     : Dono taraf mila
    - NO_SALE  : Sirf Call Center mein
    - ORPHAN   : Sirf Client mein

Primary sale rule (filhal):
    1. Minutes se match (closest)
    2. Agar minutes nahi → date se match (closest)
"""

import pandas as pd
from app.core.normalize import clean_phone_column, clean_number_column


def prepare_client(df, columns_map):
    """Client DataFrame ko standard form mein laao"""
    result = pd.DataFrame()
    
    if "phone" in columns_map:
        phone_col = columns_map["phone"]
        result["phone"] = df[phone_col].apply(lambda x: str(x) if pd.notna(x) else None)
        clean_phone_column(result, "phone")
    
    for std_name, actual_col in columns_map.items():
        if std_name == "phone":
            continue
        result[std_name] = df[actual_col]
    
    for col in ["price", "amount", "revenue", "minutes", "calls"]:
        if col in result.columns:
            clean_number_column(result, col)
    
    return result


def prepare_callcenter(df, columns_map):
    """Call Center DataFrame ko standard form mein laao"""
    result = pd.DataFrame()
    
    if "phone" in columns_map:
        phone_col = columns_map["phone"]
        result["phone"] = df[phone_col].apply(lambda x: str(x) if pd.notna(x) else None)
        clean_phone_column(result, "phone")
    
    for std_name, actual_col in columns_map.items():
        if std_name == "phone":
            continue
        result[std_name] = df[actual_col]
    
    for col in ["price", "amount", "revenue", "minutes", "calls"]:
        if col in result.columns:
            clean_number_column(result, col)
    
    return result


def _pick_primary_call(cc_group, sale_row):
    """
    CC calls ke group mein se primary call choose karo.
    
    Rule:
        1. Minutes closest match
        2. Agar minutes nahi → date closest
        3. Warna → pehli call
    """
    if len(cc_group) == 0:
        return None
    
    # ─── Try 1: Minutes match ───
    if "minutes" in cc_group.columns and "minutes" in sale_row.index:
        sale_minutes_raw = sale_row["minutes"]
        sale_minutes = pd.to_numeric(sale_minutes_raw, errors="coerce")
        
        if pd.notna(sale_minutes):
            cc_minutes = pd.to_numeric(cc_group["minutes"], errors="coerce")
            if cc_minutes.notna().any():
                diff = (cc_minutes - float(sale_minutes)).abs()
                if diff.notna().any():
                    closest_idx = diff.idxmin()
                    return closest_idx
    
    # ─── Try 2: Date match ───
    if "date" in cc_group.columns and "date" in sale_row.index:
        sale_date = pd.to_datetime(sale_row["date"], errors="coerce")
        if pd.notna(sale_date):
            cc_dates = pd.to_datetime(cc_group["date"], errors="coerce")
            if cc_dates.notna().any():
                diff = (cc_dates - sale_date).abs()
                if diff.notna().any():
                    closest_idx = diff.idxmin()
                    return closest_idx
    
    # ─── Fallback: Pehli call ───
    return cc_group.index[0]


def match_data(client_df, cc_df):
    """
    Client aur CC data match karo Phone # par.
    
    Returns: dict with keys:
        sold       — Dono mein mila (sale 1 baar per phone)
        no_sale    — Sirf CC mein (including non-primary sold calls)
        orphan     — Sirf Client mein
        summary    — Counts
    """
    
    # ─────────── Phone Sets ───────────
    client_phones = set(client_df["phone"].dropna().unique())
    cc_phones = set(cc_df["phone"].dropna().unique())
    
    common = client_phones & cc_phones
    only_cc = cc_phones - client_phones
    only_client = client_phones - cc_phones
    
    # ─────────── Client Duplicates Remove ───────────
    client_unique = client_df.copy()
    
    if "date" in client_unique.columns:
        client_unique["_date_parsed"] = pd.to_datetime(
            client_unique["date"], errors="coerce"
        )
        client_unique = client_unique.sort_values("_date_parsed", ascending=False)
        client_unique = client_unique.drop_duplicates(subset=["phone"], keep="first")
        client_unique = client_unique.drop(columns=["_date_parsed"])
    else:
        client_unique = client_unique.drop_duplicates(subset=["phone"], keep="first")
    
    # ─────────── Category Filter ───────────
    client_sold = client_unique[client_unique["phone"].isin(common)].copy()
    cc_sold = cc_df[cc_df["phone"].isin(common)].copy()
    
    no_sale_cc = cc_df[cc_df["phone"].isin(only_cc)].copy()
    orphan = client_unique[client_unique["phone"].isin(only_client)].copy()
    
    # ─────────── Primary Sale Determine ───────────
    sold_primary_rows = []
    sold_other_rows = []
    
    for phone in common:
        cc_group = cc_sold[cc_sold["phone"] == phone].copy()
        sale_rows = client_sold[client_sold["phone"] == phone]
        
        if len(cc_group) == 0 or len(sale_rows) == 0:
            continue
        
        sale_row = sale_rows.iloc[0]
        primary_idx = _pick_primary_call(cc_group, sale_row)
        
        for idx, row in cc_group.iterrows():
            row_dict = row.to_dict()
            
            # Client data merge karo
            row_dict["amount"] = sale_row.get("amount", None)
            row_dict["revenue"] = sale_row.get("revenue", None)
            row_dict["price"] = sale_row.get("price", None)
            
            if idx == primary_idx:
                row_dict["_is_primary_sale"] = True
                sold_primary_rows.append(row_dict)
            else:
                row_dict["_is_primary_sale"] = False
                sold_other_rows.append(row_dict)
    
    # ─── Sold DataFrame ───
    sold = pd.DataFrame(sold_primary_rows + sold_other_rows)
    
    # ─── No-Sale mein non-primary sold calls bhi add karo ───
    non_primary_sold = pd.DataFrame(sold_other_rows)
    
    if len(non_primary_sold) > 0:
        no_sale_extra = non_primary_sold.copy()
        no_sale_extra["amount"] = None
        no_sale_extra["revenue"] = None
        no_sale_extra["price"] = None
        if "_is_primary_sale" in no_sale_extra.columns:
            no_sale_extra = no_sale_extra.drop(columns=["_is_primary_sale"])
        
        no_sale = pd.concat([no_sale_cc, no_sale_extra], ignore_index=True, sort=False)
    else:
        no_sale = no_sale_cc
    
    # ─────────── Summary ───────────
    summary = {
        "client_total": len(client_df),
        "client_unique_sales": len(client_unique),
        "cc_total": len(cc_df),
        "client_unique_phones": len(client_phones),
        "cc_unique_phones": len(cc_phones),
        "sold_phones": len(common),
        "no_sale_phones": len(only_cc),
        "orphan_phones": len(only_client),
        "sold_rows": len(sold),
        "no_sale_rows": len(no_sale),
        "orphan_rows": len(orphan),
        "duplicates_removed": len(client_df) - len(client_unique),
        "primary_sales": len(sold_primary_rows),
    }
    
    return {
        "sold": sold,
        "no_sale": no_sale,
        "orphan": orphan,
        "summary": summary,
    }