"""
upload_page.py — Upload + Merge page
Multiple files support WITH per-file normalization.
"""

import streamlit as st
import pandas as pd
from app.config import get
from app.core.reader import read_file
from app.core.normalize import detect_columns
from app.core.matcher import match_data
from app.utils.session import has_both_files, has_result, get_combined_client, get_combined_cc


def normalize_single_file(df, col_config, source_name):
    """
    Ek single file ko normalize karo — standard column names do.
    
    Returns: normalized DataFrame with standard columns
             (phone, price, amount, minutes, team, dialer, date, calls)
    """
    # Detect columns is specific file mein
    mapping = detect_columns(df, col_config)
    
    if "phone" not in mapping:
        return None, f"'{source_name}' mein Phone column nahi mila"
    
    # Naya DataFrame banao — standard column names ke saath
    normalized = pd.DataFrame()
    
    for std_name, actual_col in mapping.items():
        normalized[std_name] = df[actual_col]
    
    # Source tracking
    normalized["_source_file"] = source_name
    
    # Extra Columns bhi rakho (jo standard nahi hain) — prefixed
    standard_actuals = set(mapping.values())
    for col in df.columns:
        if col not in standard_actuals and not col.startswith("_"):
            normalized[f"extra_{col}"] = df[col]
    
    return normalized, None


def process_uploaded_files(files, side_key, col_config):
    """
    Files ko padho, har ek ko normalize karo, phir combine karo.
    """
    normalized_dfs = []
    filenames = []
    errors = []
    
    for f in files:
        try:
            df = read_file(f, f.name)
            normalized, err = normalize_single_file(df, col_config, f.name)
            
            if err:
                errors.append(err)
                continue
            
            normalized_dfs.append(normalized)
            filenames.append(f.name)
        
        except Exception as e:
            errors.append(f"❌ {f.name}: {e}")
    
    if not normalized_dfs:
        return None, 0, 0, errors
    
    # Combine — ab columns standard hain, isliye clean merge hoga
    combined = pd.concat(normalized_dfs, ignore_index=True, sort=False)
    
    st.session_state[f"{side_key}_dfs"] = normalized_dfs
    st.session_state[f"{side_key}_files"] = filenames
    
    return combined, len(filenames), len(combined), errors


def render():
    st.title("📥 Upload Data")
    st.caption("Upload one or more files — they will be auto-combined")
    
    st.divider()
    
    col_config = get("columns", {})
    
    col1, col2 = st.columns(2)
    
    # ═══ CLIENT UPLOAD ═══
    with col1:
        st.subheader("🏢 Client Data (Sales)")
        st.caption("One or more files — Google Sheet / XLSX / CSV / JSON")
        
        client_files = st.file_uploader(
            "Choose client files",
            type=["xlsx", "xls", "csv", "json"],
            accept_multiple_files=True,
            key="client_uploader",
        )
        
        if client_files:
            combined, count, total, errors = process_uploaded_files(
                client_files, "client", col_config
            )
            
            if combined is not None:
                st.success(f"✅ {count} file(s) loaded — Total: {total} rows")
                
                if errors:
                    with st.expander(f"⚠️ {len(errors)} file(s) skipped"):
                        for err in errors:
                            st.warning(err)
                
                with st.expander(f"📁 Files ({count})"):
                    for i, fname in enumerate(st.session_state["client_files"], 1):
                        st.write(f"{i}. `{fname}`")
                
                with st.expander("👁️ Preview (first 5 rows)"):
                    st.dataframe(combined.head(5), use_container_width=True)
                
                with st.expander("📋 Columns"):
                    st.write("**Standard Columns:**")
                    std_cols = [c for c in combined.columns if not c.startswith("extra_") and not c.startswith("_")]
                    st.write(std_cols)
                    
                    extra_cols = [c for c in combined.columns if c.startswith("extra_")]
                    if extra_cols:
                        st.write("**Extra Columns:**")
                        st.write(extra_cols)
        
        elif st.session_state.get("client_dfs"):
            count = len(st.session_state["client_dfs"])
            total = sum(len(d) for d in st.session_state["client_dfs"])
            st.info(f"📁 Already loaded: {count} file(s), {total} rows")
    
    # ═══ CC UPLOAD ═══
    with col2:
        st.subheader("📞 Call Center Data (Calls)")
        st.caption("One or more files (can be team-wise)")
        
        cc_files = st.file_uploader(
            "Choose call center files",
            type=["xlsx", "xls", "csv", "json"],
            accept_multiple_files=True,
            key="cc_uploader",
        )
        
        if cc_files:
            combined, count, total, errors = process_uploaded_files(
                cc_files, "cc", col_config
            )
            
            if combined is not None:
                st.success(f"✅ {count} file(s) loaded — Total: {total} rows")
                
                if errors:
                    with st.expander(f"⚠️ {len(errors)} file(s) skipped"):
                        for err in errors:
                            st.warning(err)
                
                with st.expander(f"📁 Files ({count})"):
                    for i, fname in enumerate(st.session_state["cc_files"], 1):
                        st.write(f"{i}. `{fname}`")
                
                with st.expander("👁️ Preview (first 5 rows)"):
                    st.dataframe(combined.head(5), use_container_width=True)
                
                with st.expander("📋 Columns"):
                    std_cols = [c for c in combined.columns if not c.startswith("extra_") and not c.startswith("_")]
                    st.write("**Standard Columns:**")
                    st.write(std_cols)
        
        elif st.session_state.get("cc_dfs"):
            count = len(st.session_state["cc_dfs"])
            total = sum(len(d) for d in st.session_state["cc_dfs"])
            st.info(f"📁 Already loaded: {count} file(s), {total} rows")
    
    st.divider()
    
    # ═══ MERGE ═══
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        merge_clicked = st.button(
            "▶️  MERGE & ANALYZE",
            type="primary",
            use_container_width=True,
            disabled=not has_both_files(),
        )
    
    if not has_both_files():
        st.info("ℹ️ Upload at least one file on both sides.")
    
    # ═══ MERGE PROCESS ═══
    if merge_clicked and has_both_files():
        with st.spinner("🔄 Merging data..."):
            try:
                client_df = get_combined_client()
                cc_df = get_combined_cc()
                
                # Phone column already standard hai (normalize_single_file se)
                if "phone" not in client_df.columns:
                    st.error("❌ Phone column not found in client data")
                    st.stop()
                if "phone" not in cc_df.columns:
                    st.error("❌ Phone column not found in CC data")
                    st.stop()
                
                # Filter: price = 0, khali, negative → skip
                if "price" in client_df.columns:
                    from app.core.normalize import clean_number_column
                    clean_number_column(client_df, "price")
                    before = len(client_df)
                    client_df = client_df[
                        client_df["price"].notna() & 
                        (client_df["price"] > 0)
                    ].copy()
                    filtered = before - len(client_df)
                    if filtered > 0:
                        st.info(f"ℹ️ {filtered} rows filtered out (price empty/0/negative)")
                
                # Match
                result = match_data(client_df, cc_df)
                st.session_state["merge_result"] = result
                
                st.success("✅ Merge complete! From the left sidebar, open **Results** open")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Merge Error: {e}")
                import traceback
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())
    
    # ═══ SUMMARY ═══
    if has_result():
        st.divider()
        st.subheader("📊 Merge Summary")
        
        summary = st.session_state["merge_result"]["summary"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Sold", summary["sold_rows"])
        c2.metric("❌ No-Sale", summary["no_sale_rows"])
        c3.metric("⚠️ Orphan", summary["orphan_rows"])
        c4.metric("📞 Total Calls", summary["cc_total"])
        
        st.divider()
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_b:
            if st.button("🗑️ Clear All Data", use_container_width=True):
                from app.utils.session import clear_data
                clear_data()
                st.rerun()