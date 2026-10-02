"""
upload_page.py — Upload and merge interface.

Supports multiple files per side with per-file normalisation, then reconciles
the client dataset against the call center dataset.
"""

import pandas as pd
import streamlit as st

from app.config import get
from app.core.normalize import clean_number_column, detect_columns
from app.utils.caching import (
    download_excel_button,
    merge_frames,
    read_uploaded_file,
)
from app.utils.session import (
    clear_data,
    get_combined_cc,
    get_combined_client,
    has_both_files,
    has_result,
)
from app.utils import styles


def normalize_single_file(df, col_config, source_name):
    """Normalise a single file to the tracker's standard column names.

    Returns:
        tuple: (normalized DataFrame or None, error message or None)

    Standard columns: phone, price, amount, minutes, team, dialer, date, calls.
    """
    mapping = detect_columns(df, col_config)

    if "phone" not in mapping:
        return None, f"No phone column was detected in '{source_name}'."

    normalized = pd.DataFrame()

    for std_name, actual_col in mapping.items():
        normalized[std_name] = df[actual_col]

    # Provenance
    normalized["_source_file"] = source_name
    if "_source_sheet" in df.columns:
        normalized["_source_sheet"] = df["_source_sheet"]

    # Retain non-standard columns under an `extra_` prefix
    standard_actuals = set(mapping.values())
    for col in df.columns:
        if col not in standard_actuals and not col.startswith("_"):
            normalized[f"extra_{col}"] = df[col]

    return normalized, None


def process_uploaded_files(files, side_key, col_config):
    """Read, normalise and combine a list of uploaded files.

    Returns:
        tuple: (combined DataFrame or None, file count, row count, errors)
    """
    normalized_dfs = []
    filenames = []
    errors = []

    for f in files:
        try:
            df = read_uploaded_file(f)
            normalized, err = normalize_single_file(df, col_config, f.name)

            if err:
                errors.append(err)
                continue

            normalized_dfs.append(normalized)
            filenames.append(f.name)

        except Exception as exc:  # noqa: BLE001 — reported per file
            errors.append(f"{f.name}: {exc}")

    if not normalized_dfs:
        return None, 0, 0, errors

    combined = pd.concat(normalized_dfs, ignore_index=True, sort=False)

    st.session_state[f"{side_key}_dfs"] = normalized_dfs
    st.session_state[f"{side_key}_files"] = filenames

    return combined, len(filenames), len(combined), errors


def _sheet_note(df):
    """Return a short note describing how many sheets were merged, if any."""
    if "_source_sheet" in df.columns:
        count = df["_source_sheet"].nunique()
        if count > 1:
            return f" ({count} sheets merged)"
    return ""


def _render_consolidated_downloads():
    """Offer the multi-sheet merge result as a single consolidated sheet."""
    client_ready = bool(st.session_state.get("client_dfs"))
    cc_ready = bool(st.session_state.get("cc_dfs"))
    if not (client_ready or cc_ready):
        return

    st.subheader("Consolidated Sheet (Multi-Sheet Merge)")
    st.caption(
        "Every sheet of each uploaded workbook is merged automatically into one "
        "consolidated dataset. Use the buttons below to download it."
    )

    col_client, col_cc = st.columns(2)

    if client_ready:
        df = get_combined_client()
        with col_client:
            download_excel_button(
                f"Download Client Consolidated ({len(df)} rows){_sheet_note(df)}",
                df,
                "client_consolidated.xlsx",
                sheet_name="Client_Consolidated",
                use_container_width=True,
            )

    if cc_ready:
        df = get_combined_cc()
        with col_cc:
            download_excel_button(
                f"Download Call Center Consolidated ({len(df)} rows){_sheet_note(df)}",
                df,
                "cc_consolidated.xlsx",
                sheet_name="CC_Consolidated",
                use_container_width=True,
            )

    st.divider()
def _render_side(uploader, side_key, col_config):
    """Render one upload column (client or call center) and return its metrics."""
    if uploader:
        combined, count, total, errors = process_uploaded_files(uploader, side_key, col_config)
        if combined is None:
            return 0, 0, 0

        st.success(
            f"{count} file(s) loaded successfully — {total} row(s) total{_sheet_note(combined)}"
        )

        if errors:
            with st.expander(f"{len(errors)} file(s) could not be processed"):
                for err in errors:
                    st.warning(err)

        with st.expander(f"Files ({count})"):
            for i, fname in enumerate(st.session_state[f"{side_key}_files"], 1):
                st.write(f"{i}. `{fname}`")

        with st.expander("Preview (first 5 rows)"):
            st.dataframe(combined.head(5), use_container_width=True)

        with st.expander("Columns"):
            standard = [
                c for c in combined.columns
                if not c.startswith("extra_") and not c.startswith("_")
            ]
            st.write("**Standard columns:**")
            st.write(standard)

            extra = [c for c in combined.columns if c.startswith("extra_")]
            if extra:
                st.write("**Additional columns:**")
                st.write(extra)

        return count, total, len(errors)

    frames = st.session_state.get(f"{side_key}_dfs") or []
    if frames:
        count = len(frames)
        total = sum(len(d) for d in frames)
        st.info(f"Already loaded: {count} file(s), {total} row(s).")
        return count, total, 0

    return 0, 0, 0
def render():
    """Render the upload and merge page."""
    styles.page_header(
        "Upload Data",
        "Upload one or more files — every workbook sheet is combined automatically",
        icon="📥",
    )

    st.divider()

    col_config = get("columns", {})

    col_client, col_cc = st.columns(2)

    # ═══ CLIENT UPLOAD ═══
    with col_client:
        st.subheader("Client Data (Sales)")
        st.caption("One or more files — Excel, CSV or JSON")

        client_files = st.file_uploader(
            "Choose client files",
            type=["xlsx", "xls", "csv", "json"],
            accept_multiple_files=True,
            key="client_uploader",
        )
        _render_side(client_files, "client", col_config)

    # ═══ CALL CENTER UPLOAD ═══
    with col_cc:
        st.subheader("Call Center Data (Calls)")
        st.caption("One or more files (may be split per team)")

        cc_files = st.file_uploader(
            "Choose call center files",
            type=["xlsx", "xls", "csv", "json"],
            accept_multiple_files=True,
            key="cc_uploader",
        )
        _render_side(cc_files, "cc", col_config)

    st.divider()

    # ═══ CONSOLIDATED SHEET DOWNLOADS (multi-sheet merge) ═══
    _render_consolidated_downloads()

    # ═══ MERGE ═══
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        merge_clicked = st.button(
            "Merge & Analyse",
            type="primary",
            use_container_width=True,
            disabled=not has_both_files(),
        )

    if not has_both_files():
        st.info("Upload at least one file on both sides to enable the merge.")

    # ═══ MERGE PROCESS ═══
    if merge_clicked and has_both_files():
        with st.spinner("Merging datasets…"):
            try:
                client_df = get_combined_client()
                cc_df = get_combined_cc()

                if client_df is None or "phone" not in client_df.columns:
                    st.error("No phone column was detected in the client data.")
                    st.stop()
                if cc_df is None or "phone" not in cc_df.columns:
                    st.error("No phone column was detected in the call center data.")
                    st.stop()

                # Work on copies — the session frames are shared.
                client_df = client_df.copy()
                cc_df = cc_df.copy()

                # Filter: exclude rows with an empty, zero or negative price
                if "price" in client_df.columns:
                    clean_number_column(client_df, "price")
                    before = len(client_df)
                    client_df = client_df[
                        client_df["price"].notna() & (client_df["price"] > 0)
                    ].copy()
                    filtered = before - len(client_df)
                    if filtered > 0:
                        st.info(
                            f"{filtered} row(s) were excluded because the price was "
                            "empty, zero or negative."
                        )

                result = merge_frames(client_df, cc_df)
                st.session_state["merge_result"] = result

                st.success(
                    "Merge completed successfully. Open the **Results** page to review the outcome."
                )
                st.balloons()

            except Exception as exc:  # noqa: BLE001 — surfaced to the user
                st.error(f"Merge failed: {exc}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())

    # ═══ SUMMARY ═══
    if has_result():
        st.divider()
        st.subheader("Merge Summary")

        summary = st.session_state["merge_result"]["summary"]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Sold", summary["sold_rows"])
        c2.metric("No-Sale", summary["no_sale_rows"])
        c3.metric("Orphan", summary["orphan_rows"])
        c4.metric("Duplicate Sales", summary.get("duplicate_sale_phones", 0))
        c5.metric("Total Calls", summary["cc_total"])

        st.divider()
        col_left, col_center, col_right = st.columns([1, 1, 1])
        with col_center:
            if st.button("Clear All Data", use_container_width=True):
                clear_data()
                st.rerun()