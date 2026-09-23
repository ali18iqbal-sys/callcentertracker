"""
reports.py — Custom report generation engine
Phone # aur ID columns ko numeric metric se exclude karta hai.
"""

import pandas as pd


# ─────────────── Columns jo numeric NAHI hain ───────────────
# Yeh columns hamesha ID ki tarah treat honge, kabhi sum/average nahi
NON_METRIC_COLUMNS = {
    "phone", "phone_number", "phone #", "mobile", "contact",
    "id", "customer_id", "order_id", "dialer_id", "team_id",
    "source_file", "_source_file", "_status",
}


OPERATIONS = {
    "sum":      "Sum (A + B)",
    "subtract": "Subtract (A - B)",
    "multiply": "Multiply (A × B)",
    "divide":   "Divide (A ÷ B)",
    "count":    "Count rows",
    "average":  "Average of A",
}


def _is_id_column(col_name):
    """Column ka naam ID type hai?"""
    if not col_name:
        return False
    name = str(col_name).lower().strip()
    if name in NON_METRIC_COLUMNS:
        return True
    # Jisme "phone" ya "_id" ya " id" ho
    if "phone" in name:
        return True
    if name.endswith("_id") or name.endswith(" id"):
        return True
    if name == "id":
        return True
    return False


def _looks_like_phone_or_id(series):
    """Values dekh kar pata karo ke yeh ID/phone hai?"""
    try:
        values = pd.to_numeric(series, errors="coerce").dropna()
        if len(values) == 0:
            return False
        # Agar average value 100 million se zyada hai, yeh shayad phone/ID hai
        if values.mean() > 100_000_000:
            return True
        # Agar sab values integer aur 8 digit se zyada lambi hain
        if (values > 10_000_000).all():
            return True
    except Exception:
        pass
    return False


def get_available_columns(df):
    """
    Available columns list karo — phone/id ko numeric se exclude.
    """
    if df is None or len(df) == 0:
        return {"numeric": [], "categorical": [], "all": []}
    
    numeric_cols = []
    categorical_cols = []
    
    for col in df.columns:
        if col.startswith("_"):
            continue
        
        # ID/Phone columns skip karo
        if _is_id_column(col):
            categorical_cols.append(col)
            continue
        
        # Values check karo
        if pd.api.types.is_numeric_dtype(df[col]):
            # Value check — agar phone jaisi hai toh skip
            if _looks_like_phone_or_id(df[col]):
                categorical_cols.append(col)
            else:
                numeric_cols.append(col)
        else:
            test = pd.to_numeric(df[col], errors="coerce")
            if test.notna().sum() > len(df) * 0.5 and not _looks_like_phone_or_id(test):
                numeric_cols.append(col)
            else:
                categorical_cols.append(col)
    
    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "all": numeric_cols + categorical_cols,
    }


def apply_calculation(df, col_a, operation, col_b=None, output_name="result"):
    """Ek calculation apply karo"""
    df = df.copy()
    
    if operation == "sum":
        if col_b is None:
            df[output_name] = pd.to_numeric(df[col_a], errors="coerce")
        else:
            df[output_name] = (
                pd.to_numeric(df[col_a], errors="coerce") + 
                pd.to_numeric(df[col_b], errors="coerce")
            )
    elif operation == "subtract":
        if col_b is None:
            raise ValueError("Subtract ke liye Column B zaroori hai")
        df[output_name] = (
            pd.to_numeric(df[col_a], errors="coerce") - 
            pd.to_numeric(df[col_b], errors="coerce")
        )
    elif operation == "multiply":
        if col_b is None:
            raise ValueError("Multiply ke liye Column B zaroori hai")
        df[output_name] = (
            pd.to_numeric(df[col_a], errors="coerce") * 
            pd.to_numeric(df[col_b], errors="coerce")
        )
    elif operation == "divide":
        if col_b is None:
            raise ValueError("Divide ke liye Column B zaroori hai")
        b = pd.to_numeric(df[col_b], errors="coerce").replace(0, pd.NA)
        df[output_name] = pd.to_numeric(df[col_a], errors="coerce") / b
    elif operation == "count":
        df[output_name] = 1
    elif operation == "average":
        df[output_name] = pd.to_numeric(df[col_a], errors="coerce")
    else:
        raise ValueError(f"Operation support nahi: {operation}")
    
    return df


def filter_by_date(df, date_col, start_date, end_date):
    """Date range filter"""
    if date_col not in df.columns:
        return df
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    mask = (dates >= pd.Timestamp(start_date)) & (dates <= pd.Timestamp(end_date))
    return df[mask]


def generate_report(df, group_by=None, metric_col=None, aggregation="sum"):
    """Group-by report generate karo"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    if group_by is None:
        if metric_col and metric_col in df.columns:
            values = pd.to_numeric(df[metric_col], errors="coerce")
            if aggregation == "sum":
                result = values.sum()
            elif aggregation == "count":
                result = len(df)
            elif aggregation == "mean":
                result = values.mean()
            else:
                result = values.sum()
            
            return pd.DataFrame([{
                "Metric": metric_col,
                "Aggregation": aggregation,
                "Value": round(result, 2) if isinstance(result, float) else result,
            }])
        else:
            return pd.DataFrame([{"Total Rows": len(df)}])
    
    if group_by not in df.columns:
        return pd.DataFrame()
    
    if aggregation == "count" or metric_col is None:
        result = df.groupby(group_by).size().reset_index(name="Count")
    else:
        df_copy = df.copy()
        df_copy[metric_col] = pd.to_numeric(df_copy[metric_col], errors="coerce")
        agg_func = "sum" if aggregation == "sum" else "mean"
        result = df_copy.groupby(group_by)[metric_col].agg(agg_func).reset_index()
        result.columns = [group_by, f"{metric_col} ({aggregation})"]
    
    last_col = result.columns[-1]
    result = result.sort_values(last_col, ascending=False).reset_index(drop=True)
    
    if len(result) > 1:
        total_row = {group_by: "TOTAL"}
        for col in result.columns[1:]:
            total_row[col] = result[col].sum()
        result = pd.concat([result, pd.DataFrame([total_row])], ignore_index=True)
    
    return result


def get_numeric_summary(df, columns):
    """
    Selected columns ka summary do.
    
    ⚠️ Phone/ID columns ko automatically skip karo.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    summary = []
    for col in columns:
        if col not in df.columns:
            continue
        
        # ID columns skip
        if _is_id_column(col):
            continue
        
        values = pd.to_numeric(df[col], errors="coerce")
        
        # Value check — phone jaisi ho toh skip
        if _looks_like_phone_or_id(values):
            continue
        
        summary.append({
            "Column": col,
            "Sum": round(values.sum(), 2) if not pd.isna(values.sum()) else 0,
            "Average": round(values.mean(), 2) if not pd.isna(values.mean()) else 0,
            "Min": round(values.min(), 2) if not pd.isna(values.min()) else 0,
            "Max": round(values.max(), 2) if not pd.isna(values.max()) else 0,
            "Count": int(values.notna().sum()),
        })
    
    return pd.DataFrame(summary)


def get_calls_summary(df):
    """
    Calls ka summary — Kitni rows hain, unique phones kitne hain, etc.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    summary = {
        "Total Records (Calls)": len(df),
    }
    
    # Unique phones
    phone_col = None
    for col in df.columns:
        if _is_id_column(col) and "phone" in str(col).lower():
            phone_col = col
            break
    
    if phone_col:
        summary["Unique Phone Numbers"] = df[phone_col].nunique()
    
    # Status breakdown agar hai
    if "_status" in df.columns:
        status_counts = df["_status"].value_counts()
        for status, count in status_counts.items():
            summary[f"Status: {status}"] = int(count)
    
    # DataFrame banao
    rows = [{"Metric": k, "Value": v} for k, v in summary.items()]
    return pd.DataFrame(rows)