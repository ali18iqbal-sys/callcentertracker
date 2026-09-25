"""
performance_page.py — Team/Dialer performance dashboard
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from app.utils.session import has_result
from app.core.analytics import team_performance, dialer_performance, overall_stats


def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Performance")
    return output.getvalue()


def render():
    st.title("📈 Performance Dashboard")
    
    if not has_result():
        st.warning("⚠️ Please upload and merge first")
        st.info("👉 From the left sidebar, open **Upload** page open")
        return
    
    result = st.session_state["merge_result"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]
    
    # ═══ OVERALL STATS ═══
    stats = overall_stats(sold, no_sale, orphan)
    
    st.subheader("🎯 Overall Performance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📞 Total Calls", f"{stats['total_calls']:,}")
    c2.metric("✅ Sales", f"{stats['total_sales']:,}")
    c3.metric("🎯 Conversion", f"{stats['conversion_pct']}%")
    c4.metric("💰 Total Amount", f"{stats['total_amount']:,.0f}")
    
    st.divider()
    
    # ═══ TABS: TEAM / DIALER ═══
    tab1, tab2 = st.tabs(["👥 Team-wise", "📱 Dialer-wise"])
    
    # ─── TEAM ───
    with tab1:
        team_df = team_performance(sold, no_sale)
        
        if len(team_df) > 0:
            st.caption("Team-wise performance (sorted by amount)")
            st.dataframe(
                team_df,
                use_container_width=True,
                height=400,
                column_config={
                    "team": "Team",
                    "calls": st.column_config.NumberColumn("Calls", format="%d"),
                    "sales": st.column_config.NumberColumn("Sales", format="%d"),
                    "conversion_pct": st.column_config.NumberColumn("Conv %", format="%.2f%%"),
                    "amount": st.column_config.NumberColumn("Amount", format="%,.0f"),
                },
            )
            
            # Chart
            st.subheader("📊 Conversion % (Team-wise)")
            chart_data = team_df[["team", "conversion_pct"]].set_index("team")
            st.bar_chart(chart_data)
            
            st.download_button(
                "📥 Download Team Performance (Excel)",
                df_to_excel_bytes(team_df),
                file_name="team_performance.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Team data not found — CC file must have a 'Team' column")
    
    # ─── DIALER ───
    with tab2:
        dialer_df = dialer_performance(sold, no_sale)
        
        if len(dialer_df) > 0:
            st.caption("Dialer-wise performance (sorted by amount)")
            st.dataframe(
                dialer_df,
                use_container_width=True,
                height=400,
                column_config={
                    "dialer": "Dialer",
                    "calls": st.column_config.NumberColumn("Calls", format="%d"),
                    "sales": st.column_config.NumberColumn("Sales", format="%d"),
                    "conversion_pct": st.column_config.NumberColumn("Conv %", format="%.2f%%"),
                    "amount": st.column_config.NumberColumn("Amount", format="%,.0f"),
                },
            )
            
            st.subheader("📊 Amount (Dialer-wise)")
            chart_data = dialer_df[["dialer", "amount"]].set_index("dialer")
            st.bar_chart(chart_data)
            
            st.download_button(
                "📥 Download Dialer Performance (Excel)",
                df_to_excel_bytes(dialer_df),
                file_name="dialer_performance.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Dialer data not found — CC file must have a 'Dialer' column")