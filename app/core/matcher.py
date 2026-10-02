"""
matcher.py — Client aur Call Center data ko match karne wala module.

Pipeline:
    - Client: 1 phone = 1 unique sale (Clean Client Data)
    - Duplicate client sales → Duplicate Sales / Conflict Resolution
    - CC: duplicate calls intact (CC Master)
    - Match Clean Client vs CC Master → Sold / No-Sale / Orphan
"""

import pandas as pd
from app.core.normalize import clean_phone_column, clean_number_column


def prepare_client(df, columns_map):
    """Normalise a client DataFrame to the standard form."""
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
    """Normalise a call center DataFrame to the standard form."""
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
    """Choose the primary call from a group of call center calls.

    Rules:
        1. Closest minutes match
        2. Otherwise the closest date
        3. Otherwise the first call
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


def _clean_phone_rows(df):
    """Copy + phone normalize; blank phones drop."""
    if df is None or len(df) == 0:
        return pd.DataFrame() if df is None else df.iloc[0:0].copy()

    result = df.copy()
    if "phone" not in result.columns:
        return result.iloc[0:0].copy()

    clean_phone_column(result, "phone")
    return result[result["phone"].notna() & (result["phone"] != "")].copy()


def split_client_sales(client_df):
    """
    # Split client rows into Clean (1 phone = 1 row) and Duplicate Sales.
    # Several rows for the same phone are conflicts and are never auto-credited.
    """
    if client_df is None or len(client_df) == 0:
        empty = pd.DataFrame() if client_df is None else client_df.iloc[0:0].copy()
        return empty, empty.copy(), set()

    counts = client_df.groupby("phone").size()
    conflict_phones = set(counts[counts > 1].index)
    unique_phones = set(counts[counts == 1].index)

    clean_client = client_df[client_df["phone"].isin(unique_phones)].copy()
    duplicate_sales = client_df[client_df["phone"].isin(conflict_phones)].copy()

    if len(duplicate_sales) > 0:
        duplicate_sales["_sale_count"] = duplicate_sales["phone"].map(counts)
        duplicate_sales = duplicate_sales.sort_values(["phone"]).reset_index(drop=True)

    return clean_client, duplicate_sales, conflict_phones


def match_data(client_df, cc_df):
    """
    Match the Clean Client Data against the CC Master on the phone number.

    Returns dict:
        sold, no_sale, orphan,
        duplicate_sales, duplicate_cc,
        clean_client, summary
    """
    client_raw_count = 0 if client_df is None else len(client_df)
    cc_raw_count = 0 if cc_df is None else len(cc_df)

    client_df = _clean_phone_rows(client_df)
    cc_df = _clean_phone_rows(cc_df)

    # ─────────── Client: unique vs conflicting sales ───────────
    clean_client, duplicate_sales, conflict_phones = split_client_sales(client_df)

    # Safety: Clean Client strictly 1 phone = 1 row
    if len(clean_client) > 0:
        if "date" in clean_client.columns:
            clean_client = clean_client.copy()
            clean_client["_date_parsed"] = pd.to_datetime(
                clean_client["date"], errors="coerce"
            )
            clean_client = clean_client.sort_values("_date_parsed", ascending=False)
            clean_client = clean_client.drop_duplicates(subset=["phone"], keep="first")
            clean_client = clean_client.drop(columns=["_date_parsed"])
        else:
            clean_client = clean_client.drop_duplicates(subset=["phone"], keep="first")

    # CC Master: duplicate calls intact — no drop_duplicates
    cc_master = cc_df

    duplicate_cc = (
        cc_master[cc_master["phone"].isin(conflict_phones)].copy()
        if len(cc_master) > 0 and conflict_phones
        else (cc_master.iloc[0:0].copy() if len(cc_master) > 0 else pd.DataFrame())
    )

    # ─────────── Phone Sets (conflict phones excluded from auto-match) ───────────
    client_phones = set(clean_client["phone"].dropna().unique()) if len(clean_client) else set()
    cc_phones = set(cc_master["phone"].dropna().unique()) if len(cc_master) else set()

    common = client_phones & cc_phones
    only_cc = cc_phones - client_phones - conflict_phones
    only_client = client_phones - cc_phones

    client_sold = clean_client[clean_client["phone"].isin(common)].copy() if len(clean_client) else pd.DataFrame()
    cc_sold = cc_master[cc_master["phone"].isin(common)].copy() if len(cc_master) else pd.DataFrame()

    no_sale_cc = cc_master[cc_master["phone"].isin(only_cc)].copy() if len(cc_master) else pd.DataFrame()
    orphan = clean_client[clean_client["phone"].isin(only_client)].copy() if len(clean_client) else pd.DataFrame()

    # ─────────── Primary Sale Determine ───────────
    sold_primary_rows = []
    no_sale_non_primary_rows = []

    for phone in common:
        cc_group = cc_sold[cc_sold["phone"] == phone].copy()
        sale_rows = client_sold[client_sold["phone"] == phone]

        if len(cc_group) == 0 or len(sale_rows) == 0:
            continue

        sale_row = sale_rows.iloc[0]
        primary_idx = _pick_primary_call(cc_group, sale_row)

        for idx, row in cc_group.iterrows():
            row_dict = row.to_dict()
            is_primary = (idx == primary_idx)

            if is_primary:
                row_dict["amount"] = sale_row.get("amount", None)
                row_dict["revenue"] = sale_row.get("revenue", None)
                row_dict["price"] = sale_row.get("price", None)
                row_dict["_is_primary_sale"] = True
                sold_primary_rows.append(row_dict)
            else:
                row_dict["amount"] = None
                row_dict["revenue"] = None
                row_dict["price"] = None
                row_dict["_is_primary_sale"] = False
                no_sale_non_primary_rows.append(row_dict)

    sold = pd.DataFrame(sold_primary_rows)

    non_primary_df = pd.DataFrame(no_sale_non_primary_rows)

    if len(non_primary_df) > 0:
        if "_is_primary_sale" in non_primary_df.columns:
            non_primary_df = non_primary_df.drop(columns=["_is_primary_sale"])

        no_sale = pd.concat(
            [no_sale_cc, non_primary_df],
            ignore_index=True,
            sort=False
        )
    else:
        no_sale = no_sale_cc

    if len(sold) == 0:
        sold = pd.DataFrame(
            columns=list(cc_master.columns) + ["amount", "revenue", "price", "_is_primary_sale"]
            if len(cc_master) > 0
            else ["phone", "amount", "revenue", "price", "_is_primary_sale"]
        )

    summary = {
        "client_total": client_raw_count,
        "client_unique_sales": len(clean_client),
        "cc_total": cc_raw_count if cc_raw_count else len(cc_master),
        "client_unique_phones": len(client_phones),
        "cc_unique_phones": len(cc_phones),
        "sold_phones": len(common),
        "no_sale_phones": len(only_cc),
        "orphan_phones": len(only_client),
        "sold_rows": len(sold),
        "no_sale_rows": len(no_sale),
        "orphan_rows": len(orphan),
        "duplicates_removed": len(client_df) - len(clean_client) - len(duplicate_sales),
        "duplicate_sale_phones": len(conflict_phones),
        "duplicate_sale_rows": len(duplicate_sales),
        "duplicate_cc_rows": len(duplicate_cc),
        "primary_sales": len(sold_primary_rows),
    }

    return {
        "sold": sold,
        "no_sale": no_sale,
        "orphan": orphan,
        "duplicate_sales": duplicate_sales,
        "duplicate_cc": duplicate_cc,
        "clean_client": clean_client,
        "summary": summary,
    }
