"""
reader.py — File reading utilities.

Converts Excel, CSV and JSON files into pandas DataFrames.
"""

import json
import pandas as pd


def list_excel_sheets(file):
    """Return every sheet name in an Excel workbook.

    The file is peeked at without loading the data, so both the client and call
    center sides can report how many sheets a workbook contains — which keeps
    multi-sheet merging transparent.
    """
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass
    with pd.ExcelFile(file) as xls:
        names = list(xls.sheet_names)
    # Rewind so the same handle can be reused by Streamlit
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass
    return names


def read_excel(file, sheet_name=None, return_meta=False):
    """Read an Excel file (.xlsx / .xls).

    By default every sheet is read and merged into a single consolidated
    DataFrame (multi-sheet merging). Each row carries a ``_source_sheet`` column
    so its origin can be traced. Empty and blank sheets are skipped.

    When ``sheet_name`` is supplied, only that sheet is read (used by tests and
    for backwards compatibility).

    Args:
        file: path or file-like object
        sheet_name: read only this sheet when provided
        return_meta: when True, return (df, meta) where meta is
                     {"sheets": [...], "skipped": [...], "n_sheets": int}

    Returns:
        pd.DataFrame or (pd.DataFrame, dict)
    """
    if hasattr(file, "seek"):
        try:
            file.seek(0)
        except Exception:
            pass

    if sheet_name is not None:
        df = pd.read_excel(file, sheet_name=sheet_name, dtype=str)
        if return_meta:
            return df, {"sheets": [str(sheet_name)], "skipped": [], "n_sheets": 1}
        return df

    frames = []
    used_sheets = []
    skipped_sheets = []

    # The context manager releases the file handle, which prevents locks on
    # temporary or uploaded files under Windows.
    with pd.ExcelFile(file) as xls:
        for name in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=name, dtype=str)
            except Exception as exc:
                skipped_sheets.append({"sheet": str(name), "reason": str(exc)[:200]})
                continue

            if df is None or df.empty:
                continue
            df = df.dropna(how="all")
            if df.empty:
                continue

            df = df.copy()
            df["_source_sheet"] = str(name)
            frames.append(df)
            used_sheets.append(str(name))

    if not frames:
        raise ValueError("No data was found in any sheet of the Excel file.")

    combined = pd.concat(frames, ignore_index=True, sort=False)

    if return_meta:
        meta = {
            "sheets": used_sheets,
            "skipped": skipped_sheets,
            "n_sheets": len(used_sheets),
        }
        return combined, meta

    return combined


def read_csv(file):
    """Read a CSV file, detecting the encoding automatically."""
    # Try UTF-8 first, then fall back to latin-1
    try:
        return pd.read_csv(file, dtype=str)
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        return pd.read_csv(file, dtype=str, encoding="latin-1")


def read_json(file):
    """Read a JSON file and convert it to a DataFrame.

    Handles the common payload shapes: a list of records, or an object that
    contains a list of records.
    """
    if hasattr(file, "read"):
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        data = json.loads(content)
    else:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

    if isinstance(data, dict):
        # Find the first list of records inside the object
        for value in data.values():
            if isinstance(value, list):
                return pd.DataFrame(value)
        # Otherwise treat it as a single record
        return pd.DataFrame([data])

    if isinstance(data, list):
        return pd.DataFrame(data)

    raise ValueError("The JSON structure could not be interpreted.")


def read_file(file, filename=None):
    """Detect the file type and read it into a DataFrame.

    Args:
        file: File object (Streamlit upload) or path
        filename: file name, required when ``file`` is a file object

    Returns:
        pandas DataFrame
    """
    if filename is None:
        if hasattr(file, "name"):
            filename = file.name
        else:
            filename = str(file)

    name = str(filename).lower()

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return read_excel(file)
    if name.endswith(".csv"):
        return read_csv(file)
    if name.endswith(".json"):
        return read_json(file)

    raise ValueError(f"Unsupported file type: {filename}")