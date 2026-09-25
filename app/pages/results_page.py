"""
results_page.py — Merge Results display
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from app.utils.session import has_result


def df_to_excel_bytes(df):
    """DataFrame ko Excel bytes mein convert karo (download ke liye)"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return output.getvalue()


def render():
    st.title("📊 Merge Results")
    
    if not has_result():
        st.warning("⚠️ Please upload and merge first")
        st.info("👉 From the left sidebar, open **Upload** page open")
        return
    
    result = st.session_state["merge_result"]
    summary = result["summary"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]
    
    # ═══ SUMMARY CARDS ═══
    st.subheader("📋 Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Sold (Matched)", summary["sold_rows"])
    c2.metric("❌ No-Sale (CC Only)", summary["no_sale_rows"])
    c3.metric("⚠️ Orphan (Client Only)", summary["orphan_rows"])
    
    st.divider()
    
    # ═══ TABS ═══
    tab1, tab2, tab3 = st.tabs([
        f"✅ Sold ({len(sold)})",
        f"❌ No-Sale ({len(no_sale)})",
        f"⚠️ Orphan ({len(orphan)})",
    ])
    
    # ─── SOLD ───
    with tab1:
        st.caption("Calls that resulted in a sale")
        if len(sold) > 0:
            st.dataframe(sold, use_container_width=True, height=400)
            st.download_button(
                "📥 Download Sold (Excel)",
                df_to_excel_bytes(sold),
                file_name="sold.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No sold records")
    
    # ─── NO SALE ───
    with tab2:
        st.caption("Calls logged in CC but no sale on client side")
        if len(no_sale) > 0:
            st.dataframe(no_sale, use_container_width=True, height=400)
            st.download_button(
                "📥 Download No-Sale (Excel)",
                df_to_excel_bytes(no_sale),
                file_name="no_sale.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No no-sale records")
    
    # ─── ORPHAN ───
    with tab3:
        st.caption("Sales on client side but no matching call in CC")
        if len(orphan) > 0:
            st.dataframe(orphan, use_container_width=True, height=400)
            st.download_button(
                "📥 Download Orphan (Excel)",
                df_to_excel_bytes(orphan),
                file_name="orphan.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No orphan records")