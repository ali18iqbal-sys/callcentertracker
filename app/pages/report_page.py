"""
from app.core.reports import (
    OPERATIONS,
    get_available_columns,
    apply_calculation,
    filter_by_date,
    generate_report,
    get_numeric_summary,
    get_calls_summary,       # ← YEH ADD KAREIN
)
report_page.py — Custom Report Builder UI
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date, timedelta
from app.utils.session import has_result
from app.core.reports import (
    OPERATIONS,
    get_available_columns,
    apply_calculation,
    filter_by_date,
    generate_report,
    get_numeric_summary,
    get_calls_summary,
)


def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()


def get_all_data():
    """Sold + No-Sale ko combine karke master data do"""
    if not has_result():
        return None
    result = st.session_state["merge_result"]
    sold = result["sold"].copy()
    no_sale = result["no_sale"].copy()
    orphan = result["orphan"].copy()
    
    # Status column add karo
    sold["_status"] = "Sold"
    no_sale["_status"] = "No-Sale"
    orphan["_status"] = "Orphan"
    
    # Combine karo
    combined = pd.concat([sold, no_sale, orphan], ignore_index=True, sort=False)
    return combined


def render():
    st.title("📊 Custom Report Builder")
    st.caption("Build your own calculation, apply filters, download report")
    
    if not has_result():
        st.warning("⚠️ Please upload and merge first")
        st.info("👉 From the left sidebar, open **Upload** page open")
        return
    
    # ═══ DATA LOAD ═══
    df = get_all_data()
    
    if df is None or len(df) == 0:
        st.error("Data load nahi hua")
        return
    
    st.success(f"✅ Data loaded: {len(df)} rows, {len(df.columns)} columns")
    
    # Available columns
    cols_info = get_available_columns(df)
    numeric_cols = cols_info["numeric"]
    categorical_cols = cols_info["categorical"]
    
    st.divider()
    
    # ═══ SECTION 1: FILTERS ═══
    st.subheader("🔍 Filters")
    
    col1, col2 = st.columns(2)
    
    # Date filter
    with col1:
        date_columns = [c for c in df.columns if "date" in c.lower()]
        
        if date_columns:
            date_col = st.selectbox("Date Column", date_columns, key="date_col_select")
            
            # Default: last 30 days
            default_start = date.today() - timedelta(days=30)
            default_end = date.today()
            
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
                key="date_range_input",
            )
            
            use_date_filter = st.checkbox("Apply date filter", value=False, key="use_date_filter")
        else:
            date_col = None
            use_date_filter = False
            st.info("No date column found")
    
    # Status filter
    with col2:
        if "_status" in df.columns:
            statuses = ["Sab"] + sorted(df["_status"].unique().tolist())
            selected_status = st.multiselect(
                "Status (Sold / No-Sale / Orphan)",
                options=statuses[1:],
                default=statuses[1:],
                key="status_filter",
            )
        else:
            selected_status = None
    
    # Apply filters
    filtered_df = df.copy()
    
    if use_date_filter and date_col and len(date_range) == 2:
        filtered_df = filter_by_date(filtered_df, date_col, date_range[0], date_range[1])
    
    if selected_status is not None and "_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["_status"].isin(selected_status)]
    
    st.caption(f"📊 Filtered: **{len(filtered_df)}** rows (total {len(df)})")
    
    st.divider()
    
    # ═══ SECTION 2: CALCULATION ═══
    st.subheader("🧮 Custom Calculation")
    st.caption("Naya column banao — Column A + Operation + Column B")
    
    with st.expander("➕ Add new calculated column", expanded=False):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
        
        with c1:
            col_a = st.selectbox("Column A", numeric_cols, key="calc_col_a")
        
        with c2:
            operation = st.selectbox(
                "Operation",
                list(OPERATIONS.keys()),
                format_func=lambda x: OPERATIONS[x],
                key="calc_operation",
            )
        
        with c3:
            # Column B — sirf tab chahiye jab operation do columns leta ho
            needs_b = operation in ("sum", "subtract", "multiply", "divide")
            if needs_b:
                col_b = st.selectbox("Column B", numeric_cols, key="calc_col_b")
            else:
                col_b = None
                st.caption("(Column B not required)")
        
        with c4:
            output_name = st.text_input("Output Column Name", value="calculated", key="calc_output_name")
        
        if st.button("🧮 Apply Calculation", key="apply_calc_btn"):
            try:
                filtered_df = apply_calculation(filtered_df, col_a, operation, col_b, output_name)
                st.session_state["report_filtered_df"] = filtered_df
                st.success(f"✅ Calculated column '{output_name}' added successfully")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Agar pehle calculation ho chuki hai
    if "report_filtered_df" in st.session_state and st.session_state["report_filtered_df"] is not None:
        filtered_df = st.session_state["report_filtered_df"]
        st.info(f"ℹ️ Calculated column is active — total columns: {len(filtered_df.columns)}")
        
        if st.button("🔄 Reset Calculated Columns", key="reset_calc_btn"):
            st.session_state["report_filtered_df"] = None
            st.rerun()
    
    st.divider()
    
    # ═══ SECTION 3: GROUP BY REPORT ═══
    st.subheader("📊 Group Report")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        group_options = ["((No Grouping))"] + categorical_cols
        group_by = st.selectbox("Group By", group_options, key="group_by_select")
        group_by = None if group_by == "((No Grouping))" else group_by
    
    with c2:
        metric_options = ["((Count Only))"] + numeric_cols
        metric_col = st.selectbox("Metric Column", metric_options, key="metric_col_select")
        metric_col = None if metric_col == "((Count Only))" else metric_col
    
    with c3:
        aggregation = st.selectbox(
            "Aggregation",
            ["sum", "count", "mean"],
            format_func=lambda x: {"sum": "Sum", "count": "Count", "mean": "Average"}[x],
            key="aggregation_select",
        )
    
    if st.button("📊 Generate Report", type="primary", key="gen_report_btn"):
        try:
            report_df = generate_report(
                filtered_df,
                group_by=group_by,
                metric_col=metric_col,
                aggregation=aggregation,
            )
            
            if len(report_df) == 0:
                st.warning("No data found")
            else:
                st.subheader("📋 Report Result")
                st.dataframe(report_df, use_container_width=True, hide_index=True)
                
                # Download button
                st.download_button(
                    "📥 Download Report (Excel)",
                    df_to_excel_bytes(report_df),
                    file_name=f"report_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                
                # Chart (agar 2 columns hain aur total row nahi hai)
                if len(report_df.columns) == 2 and len(report_df) > 1:
                    chart_col = report_df.columns[1]
                    # Total row hata do chart ke liye
                    chart_data = report_df[report_df[report_df.columns[0]] != "TOTAL"]
                    if len(chart_data) > 0:
                        st.subheader("📈 Chart")
                        st.bar_chart(chart_data.set_index(report_df.columns[0])[chart_col])
        
        except Exception as e:
            st.error(f"❌ Report Error: {e}")
    
    st.divider()
    
       # ═══ SECTION 4: SUMMARY ═══
    st.subheader("📋 Summary")
    
    # ─── A) Calls Summary (Total rows, unique phones) ───
    st.markdown("**📞 Calls & Records Summary**")
    calls_summary = get_calls_summary(filtered_df)
    if len(calls_summary) > 0:
        st.dataframe(calls_summary, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # ─── B) Numeric Columns Summary ───
    st.markdown("**📊 Numeric Columns Summary**")
    st.caption("Only metric columns (phone/ID excluded)")
    
    selected_metrics = st.multiselect(
        "Select columns",
        numeric_cols,
        default=numeric_cols[:min(5, len(numeric_cols))],
        key="summary_metrics_select",
    )
    
    if selected_metrics:
        summary_df = get_numeric_summary(filtered_df, selected_metrics)
        if len(summary_df) > 0:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            st.download_button(
                "📥 Download Summary (Excel)",
                df_to_excel_bytes(summary_df),
                file_name=f"summary_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No valid numeric columns found")
    
    # ═══ SECTION 5: RAW DATA PREVIEW ═══
    with st.expander("👁️ Filtered Data Preview (full)"):
        st.dataframe(filtered_df, use_container_width=True, height=400)
        
        st.download_button(
            "📥 Download Full Filtered Data (Excel)",
            df_to_excel_bytes(filtered_df),
            file_name=f"filtered_data_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )