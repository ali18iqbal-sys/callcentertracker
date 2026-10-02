"""
excel_io.py — Excel export helpers.

Reusable helpers used by the Upload page to download a merged dataset as a
single consolidated sheet.
"""

from io import BytesIO
import pandas as pd


def df_to_excel_bytes(df, sheet_name="Data"):
    """Convert a DataFrame to single-sheet Excel bytes."""
    if df is None:
        df = pd.DataFrame()
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=str(sheet_name)[:31] or "Data")
    return output.getvalue()


def sheets_to_excel_bytes(sheets):
    """Convert multiple DataFrames into a multi-sheet Excel workbook.

    Args:
        sheets: dict {sheet_name: DataFrame}

    Note:
        This is a safety helper. The default multi-sheet merge behaviour is to
        produce a single consolidated sheet; use this only when the original
        sheets must be preserved separately.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        wrote_any = False
        for name, df in (sheets or {}).items():
            if df is None:
                continue
            safe = str(name)[:31] or "Sheet"
            df.to_excel(writer, index=False, sheet_name=safe)
            wrote_any = True
        if not wrote_any:
            pd.DataFrame().to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()
