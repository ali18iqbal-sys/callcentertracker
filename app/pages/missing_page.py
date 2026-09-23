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
        st.warning("⚠️ Pehle upload aur merge karein")
        st.info("👉 Left sidebar se **Upload** page kholein")
        return
    
    result = st.session_state["merge_result"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]
    
    st.caption("Yeh report dikhati hai ke kahan data match nahi hua")
    st.divider()
    
    # ═══ SUMMARY ═══
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Sold (Matched)", len(sold))
    c2.metric("❌ No-Sale (CC only)", len(no_sale))
    c3.metric("⚠️ Orphan (Client only)", len(orphan))
    
    st.divider()
    
    # ═══ TABS ═══
    tab1, tab2 = st.tabs([
        f"⚠️ Orphan Sales ({len(orphan)})",
        f"❌ No-Sale Calls ({len(no_sale)})",
    ])
    
    # ─── ORPHAN ───
    with tab1:
        st.subheader("⚠️ Orphan Sales")
        st.caption("Client sheet mein hai, lekin Call Center ki file mein call nahi mili")
        
        if len(orphan) > 0:
            st.warning(f"**{len(orphan)}** phone # client mein hain lekin CC ki file mein nahi mile")
            
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
            **Possible reasons:**
            - CC ki file adhoori hai (kuch dialers ka data missing)
            - Phone # ka format alag hai (auto-fix ho chuka hai)
            - Client ne ghalat phone # bheja
            """)
        else:
            st.success("✅ Koi orphan record nahi — sab client phones CC mein mile")
    
    # ─── NO-SALE ───
    with tab2:
        st.subheader("❌ No-Sale Calls")
        st.caption("Call Center ne call ki, lekin us phone # par sale nahi hui")
        
        if len(no_sale) > 0:
            st.warning(f"**{len(no_sale)}** calls jinke against sale nahi hui")
            
            st.dataframe(no_sale, use_container_width=True, height=400)
            
            st.download_button(
                "📥 Download No-Sale (Excel)",
                df_to_excel_bytes(no_sale),
                file_name="no_sale_calls.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            
            st.info("""
            **Yeh calls valid hain** — sirf in par sale nahi hui.
            Team/Dialer performance mein yeh "effort without sale" hain.
            """)
        else:
            st.success("✅ Koi no-sale call nahi — sab calls par sale hui!")