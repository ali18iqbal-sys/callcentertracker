"""
matcher.py — Client aur Call Center data ko match karne wala module.
Phone # par match karta hai aur 3 categories banata hai:
    - SOLD     : Dono taraf mila (sale 1 baar count)
    - NO_SALE  : Sirf Call Center mein
    - ORPHAN   : Sirf Client mein
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


def match_data(client_df, cc_df):
    """
    Client aur CC data match karo Phone # par.
    
    Returns: dict with keys:
        sold       — Dono mein mila (sale 1 baar per phone)
        no_sale    — Sirf CC mein
        orphan     — Sirf Client mein
        summary    — Counts
    """
    
    # ─────────────── Phone Sets ───────────────
    client_phones = set(client_df["phone"].dropna().unique())
    cc_phones = set(cc_df["phone"].dropna().unique())
    
    common = client_phones & cc_phones
    only_cc = cc_phones - client_phones
    only_client = client_phones - cc_phones
    
    # ─────────────── Duplicate Sales Remove ───────────────
    # Ek phone # par sirf 1 sale rakho (latest)
    client_unique = client_df.copy()
    
    if "date" in client_unique.columns:
        # Date ke hisaab se latest rakho
        client_unique["_date_parsed"] = pd.to_datetime(
            client_unique["date"], errors="coerce"
        )
        client_unique = client_unique.sort_values("_date_parsed", ascending=False)
        client_unique = client_unique.drop_duplicates(subset=["phone"], keep="first")
        client_unique = client_unique.drop(columns=["_date_parsed"])
    else:
        # Date nahi hai toh pehli rakho
        client_unique = client_unique.drop_duplicates(subset=["phone"], keep="first")
    
    # ─────────────── Category Filter ───────────────
    # SOLD: dono mein hai
    client_sold = client_unique[client_unique["phone"].isin(common)].copy()
    cc_sold = cc_df[cc_df["phone"].isin(common)].copy()
    
    # NO_SALE: sirf CC
    no_sale = cc_df[cc_df["phone"].isin(only_cc)].copy()
    
    # ORPHAN: sirf Client
    orphan = client_unique[client_unique["phone"].isin(only_client)].copy()
    
    # ─────────────── SOLD Merge ───────────────
    # CC ki saari calls rahengi, lekin client ka amount sirf 1 row par
    # Approach: CC ki calls rakhо, aur client ka data 1 baar join karo
    # Lekin sale total = 1 baar
    
    # Pehle CC calls lo (multiple ho sakti hain)
    cc_sold_tagged = cc_sold.copy()
    
    # Client ka data phone ke saath
    client_data = client_sold.copy()
    
    # Merge karo — CC calls ke saath client data
    sold = cc_sold_tagged.merge(
        client_data,
        on="phone",
        how="left",
        suffixes=("_cc", "_client"),
    )
    
    # ─── Sale amount sirf 1 row par rakho (mark karo) ───
    # Har phone ke liye pehli row mein `_is_primary_sale` = True
    if len(sold) > 0:
        sold["_is_primary_sale"] = False
        # Sort karo date ke hisaab se (agar hai)
        if "date_cc" in sold.columns:
            sold["_sort_date"] = pd.to_datetime(sold["date_cc"], errors="coerce")
            sold = sold.sort_values(["phone", "_sort_date"])
        elif "date" in sold.columns:
            sold["_sort_date"] = pd.to_datetime(sold["date"], errors="coerce")
            sold = sold.sort_values(["phone", "_sort_date"])
        
        # Har phone ke liye pehli row ko primary mark karo
        first_indices = sold.groupby("phone").head(1).index
        sold.loc[first_indices, "_is_primary_sale"] = True
        
        # Clean up
        if "_sort_date" in sold.columns:
            sold = sold.drop(columns=["_sort_date"])
        
        sold = sold.reset_index(drop=True)
    
    # ─────────────── Summary ───────────────
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
    }
    
    return {
        "sold": sold,
        "no_sale": no_sale,
        "orphan": orphan,
        "summary": summary,
    }