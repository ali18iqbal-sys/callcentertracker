"""
caching.py — Streamlit caching layer for expensive operations.

The application's heavy work (parsing uploads, reconciling datasets,
serialising Excel exports) is wrapped here so it runs once and is reused on
every subsequent rerun and page switch:

    read_uploaded_file()  → Excel / CSV / JSON parsing of uploaded files
    merge_frames()        → Client ↔ Call Center reconciliation
    excel_bytes()         → DataFrame → Excel workbook bytes
    excel_sheets_bytes()  → multi-sheet workbook bytes

Core modules under ``app/core`` stay free of caching decorators so they remain
plain, directly testable functions; this module is the single place where the
memoisation policy is defined. Call the ``clear_*`` helpers after writing new
data to disk so stale results are never served.
"""

from io import BytesIO

import streamlit as st

from app.core.analytics import (
    dialer_performance,
    overall_stats,
    team_performance,
)
from app.core.matcher import match_data
from app.core.reader import read_file
from app.utils.excel_io import df_to_excel_bytes, sheets_to_excel_bytes

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────── File parsing ───────────────────────
@st.cache_data(show_spinner=False, max_entries=32)
def _parse_bytes(data: bytes, filename: str):
    """Parse raw file bytes into a DataFrame (cached)."""
    return read_file(BytesIO(data), filename)


def read_uploaded_file(uploaded):
    """Read a Streamlit ``UploadedFile`` through the cache.

    Identical file contents are parsed only once per session, which removes the
    noticeable delay when users switch pages or upload the same workbook twice.

    Args:
        uploaded: Streamlit UploadedFile (or any object exposing ``getvalue``).

    Returns:
        pandas.DataFrame
    """
    if hasattr(uploaded, "getvalue"):
        data = uploaded.getvalue()
    elif hasattr(uploaded, "read"):
        data = uploaded.read()
    else:
        return read_file(uploaded, getattr(uploaded, "name", str(uploaded)))

    name = getattr(uploaded, "name", "uploaded")
    if hasattr(uploaded, "seek"):
        try:
            uploaded.seek(0)
        except Exception:
            pass

    return _parse_bytes(bytes(data), str(name))


def clear_file_cache():
    """Drop cached file parses (call after replacing source files on disk)."""
    _parse_bytes.clear()


# ─────────────────────── Reconciliation ───────────────────────
@st.cache_data(show_spinner=False, max_entries=8)
def merge_frames(client_df, cc_df):
    """Run the client ↔ call center reconciliation (cached).

    ``match_data`` is a pure function, so identical inputs always produce the
    same output; caching it keeps re-runs and repeated merges instant.
    """
    return match_data(client_df, cc_df)


def clear_merge_cache():
    """Drop cached reconciliation results."""
    merge_frames.clear()


# ─────────────────────── Excel export ───────────────────────
@st.cache_data(show_spinner=False, max_entries=16)
def excel_bytes(df, sheet_name="Data"):
    """Serialise a single DataFrame to Excel bytes (cached)."""
    return df_to_excel_bytes(df, sheet_name)


@st.cache_data(show_spinner=False, max_entries=8)
def excel_sheets_bytes(sheets):
    """Serialise ``{sheet_name: DataFrame}`` to a workbook (cached)."""
    return sheets_to_excel_bytes(sheets)


def clear_excel_cache():
    """Drop cached Excel exports."""
    excel_bytes.clear()
    excel_sheets_bytes.clear()


def download_excel_button(label, df, file_name, sheet_name="Data", key=None, **kwargs):
    """Render an Excel download button backed by the export cache.

    Serialising a large DataFrame to Excel is expensive; caching the workbook
    bytes keeps every rerun and page switch responsive.

    Args:
        label: button caption
        df: DataFrame to export
        file_name: download file name
        sheet_name: worksheet name inside the workbook
        key: optional widget key
        **kwargs: additional ``st.download_button`` arguments
    """
    return st.download_button(
        label,
        data=excel_bytes(df, sheet_name),
        file_name=file_name,
        mime=EXCEL_MIME,
        key=key,
        **kwargs,
    )


# ─────────────────────── Dashboard analytics ───────────────────────
@st.cache_data(show_spinner=False, max_entries=8)
def team_metrics(sold_df, no_sale_df):
    """Team-wise conversion metrics (cached)."""
    return team_performance(sold_df, no_sale_df)


@st.cache_data(show_spinner=False, max_entries=8)
def dialer_metrics(sold_df, no_sale_df):
    """Dialer-wise conversion metrics (cached)."""
    return dialer_performance(sold_df, no_sale_df)


@st.cache_data(show_spinner=False, max_entries=8)
def summary_stats(sold_df, no_sale_df, orphan_df):
    """Overall summary statistics (cached)."""
    return overall_stats(sold_df, no_sale_df, orphan_df)


def clear_analytics_cache():
    """Drop cached dashboard analytics."""
    team_metrics.clear()
    dialer_metrics.clear()
    summary_stats.clear()


def clear_all():
    """Drop every cache managed by this module."""
    clear_file_cache()
    clear_merge_cache()
    clear_excel_cache()
    clear_analytics_cache()