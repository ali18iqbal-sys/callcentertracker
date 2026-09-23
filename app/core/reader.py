"""
reader.py — File padhne wala module
Yeh Excel, CSV, JSON files ko DataFrame mein convert karta hai.
"""

import io
import json
from pathlib import Path
import pandas as pd


def read_excel(file, sheet_name=0):
    """Excel file (.xlsx / .xls) padho"""
    return pd.read_excel(file, sheet_name=sheet_name, dtype=str)


def read_csv(file):
    """CSV file padho — encoding auto-detect karo"""
    # Try utf-8 first, phir latin-1
    try:
        return pd.read_csv(file, dtype=str)
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        return pd.read_csv(file, dtype=str, encoding="latin-1")


def read_json(file):
    """JSON file padho — different structures handle karo"""
    if hasattr(file, "read"):
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        data = json.loads(content)
    else:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    # Agar dict hai aur uske andar list hai (nested)
    if isinstance(data, dict):
        # Pehli list dhoondo
        for key, value in data.items():
            if isinstance(value, list):
                return pd.DataFrame(value)
        # Warna single-row DataFrame
        return pd.DataFrame([data])
    
    # Agar seedha list hai
    if isinstance(data, list):
        return pd.DataFrame(data)
    
    raise ValueError("JSON ka structure samajh nahi aaya")


def read_file(file, filename=None):
    """
    Automatic detect karo file type aur padho.
    
    Args:
        file: File object (Streamlit upload) ya path
        filename: File ka naam (agar file object ho)
    
    Returns:
        pandas DataFrame
    """
    # Filename nikaalo
    if filename is None:
        if hasattr(file, "name"):
            filename = file.name
        else:
            filename = str(file)
    
    name = str(filename).lower()
    
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return read_excel(file)
    elif name.endswith(".csv"):
        return read_csv(file)
    elif name.endswith(".json"):
        return read_json(file)
    else:
        raise ValueError(f"File type support nahi hai: {filename}")