"""
missing_page.py — Missing / Mismatch Report
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from app.utils.session import has_result


def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Missing")
    return output.getvalue()


def render():
    st.title("⚠️ Missing / Mismatch Report")
    
    if not has_result():
        st.warning("⚠️ Please upload and merge first")
        st.info("👉 From the left sidebar, open **Upload** page open")
        return
    
    result = st.session_state["merge_result"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]
    
    st.caption("This report shows where data did not match")
    st.divider()
    
    # ═══ SUMMARY ═══
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Sold (Matched)", len(sold))
    c2.metric("❌ No-Sale (CC Only)", len(no_sale))
    c3.metric("⚠️ Orphan (Client Only)", len(orphan))
    
    st.divider()
    
    # ═══ TABS ═══
    tab1, tab2 = st.tabs([
        f"⚠️ Orphan Sales ({len(orphan)})",
        f"❌ No-Sale Calls ({len(no_sale)})",
    ])
    
    # ─── ORPHAN ───
    with tab1:
        st.subheader("⚠️ Orphan Sales")
        st.caption("Present in client sheet but no matching call in Call Center file")
        
        if len(orphan) > 0:
            st.warning(f"**{len(orphan)}** phone numbers in client but not found in CC file")
            
            st.dataframe(orphan, use_container_width=True, height=400)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.download_button(
                    "📥 Download Orphan (Excel)",
                    df_to_excel_bytes(orphan),
                    file_name="orphan_sales.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            
            st.info("""
            **Possible Reasons:**
            - CC file is incomplete (some dialers' data missing)
            - Phone # format differs (auto-fix applied)
            - Client sent wrong phone #
            """)
        else:
            st.success("✅ No orphan records — all client phones found in CC")
    
    # ─── NO-SALE ───
    with tab2:
        st.subheader("❌ No-Sale Calls")
        st.caption("Call Center ne call ki, lekin us phone # par sale nahi hui")
        
        if len(no_sale) > 0:
            st.warning(f"**{len(no_sale)}** calls with no sale")
            
            st.dataframe(no_sale, use_container_width=True, height=400)
            
            st.download_button(
                "📥 Download No-Sale (Excel)",
                df_to_excel_bytes(no_sale),
                file_name="no_sale_calls.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            
            st.info("""
            **These calls are valid** — sirf in par sale nahi hui.
            Team/Dialer performance mein yeh "effort without sale" hain.
            """)
        else:
            st.success("✅ No no-sale calls — all calls resulted in sales!")