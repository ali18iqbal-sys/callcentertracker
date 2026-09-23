"""
matcher.py — Client aur Call Center data ko match karne wala module.
Phone # par match karta hai aur 3 categories banata hai:
    - SOLD     : Dono taraf mila
    - NO_SALE  : Sirf Call Center mein
    - ORPHAN   : Sirf Client mein
"""

import pandas as pd
from app.core.normalize import clean_phone_column, clean_number_column


def prepare_client(df, columns_map):
    """
    Client DataFrame ko standard form mein laao.
    columns_map: {standard_name: actual_column}
    """
    result = pd.DataFrame()
    
    # Phone # clean karo
    if "phone" in columns_map:
        phone_col = columns_map["phone"]
        result["phone"] = df[phone_col].apply(lambda x: str(x) if pd.notna(x) else None)
        clean_phone_column(result, "phone")
    
    # Baaki columns copy karo
    for std_name, actual_col in columns_map.items():
        if std_name == "phone":
            continue
        result[std_name] = df[actual_col]
    
    # Numeric columns clean karo
    for col in ["price", "amount", "minutes", "calls"]:
        if col in result.columns:
            clean_number_column(result, col)
    
    return result


def prepare_callcenter(df, columns_map):
    """
    Call Center DataFrame ko standard form mein laao.
    """
    result = pd.DataFrame()
    
    # Phone # clean karo
    if "phone" in columns_map:
        phone_col = columns_map["phone"]
        result["phone"] = df[phone_col].apply(lambda x: str(x) if pd.notna(x) else None)
        clean_phone_column(result, "phone")
    
    # Baaki columns copy karo
    for std_name, actual_col in columns_map.items():
        if std_name == "phone":
            continue
        result[std_name] = df[actual_col]
    
    # Numeric columns clean karo
    for col in ["price", "amount", "minutes", "calls"]:
        if col in result.columns:
            clean_number_column(result, col)
    
    return result


def match_data(client_df, cc_df):
    """
    Client aur CC data match karo Phone # par.
    
    Returns: dict with keys:
        sold       — Dono mein mila
        no_sale    — Sirf CC mein
        orphan     — Sirf Client mein
        summary    — Counts
    """
    
    # Phone # sets banao
    client_phones = set(client_df["phone"].dropna().unique())
    cc_phones = set(cc_df["phone"].dropna().unique())
    
    # Common, only_cc, only_client
    common = client_phones & cc_phones
    only_cc = cc_phones - client_phones
    only_client = client_phones - cc_phones
    
    # DataFrames filter karo
    # SOLD: Client ka data + CC ka team/dialer info
    client_sold = client_df[client_df["phone"].isin(common)].copy()
    cc_sold = cc_df[cc_df["phone"].isin(common)].copy()
    
    # NO_SALE: Sirf CC
    no_sale = cc_df[cc_df["phone"].isin(only_cc)].copy()
    
    # ORPHAN: Sirf Client
    orphan = client_df[client_df["phone"].isin(only_client)].copy()
    
    # SOLD merge karo: Client (price, amount) + CC (team, dialer)
    # Same phone par multiple CC calls ho sakti hain — sab include karo
    sold = cc_sold.merge(client_sold, on="phone", how="left", suffixes=("_cc", "_client"))
    
    summary = {
        "client_total": len(client_df),
        "cc_total": len(cc_df),
        "client_unique_phones": len(client_phones),
        "cc_unique_phones": len(cc_phones),
        "sold_phones": len(common),
        "no_sale_phones": len(only_cc),
        "orphan_phones": len(only_client),
        "sold_rows": len(sold),
        "no_sale_rows": len(no_sale),
        "orphan_rows": len(orphan),
    }
    
    return {
        "sold": sold,
        "no_sale": no_sale,
        "orphan": orphan,
        "summary": summary,
    }