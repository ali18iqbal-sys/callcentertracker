"""
report_page.py — Custom report builder interface.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.core.reports import (
    OPERATIONS,
    apply_calculation,
    filter_by_date,
    generate_report,
    get_available_columns,
    get_calls_summary,
    get_numeric_summary,
)
from app.utils import styles
from app.utils.caching import download_excel_button
from app.utils.session import has_result


def get_all_data():
    """Combine the Sold, No-Sale and Orphan datasets into a single frame."""
    if not has_result():
        return None

    result = st.session_state["merge_result"]
    sold = result["sold"].copy()
    no_sale = result["no_sale"].copy()
    orphan = result["orphan"].copy()

    sold["_status"] = "Sold"
    no_sale["_status"] = "No-Sale"
    orphan["_status"] = "Orphan"

    return pd.concat([sold, no_sale, orphan], ignore_index=True, sort=False)


def render():
    """Render the custom report builder."""
    styles.page_header(
        "Custom Report Builder",
        "Build a calculation, apply filters and download the report",
        icon="🧮",
    )

    if not has_result():
        st.warning("No merge results are available yet.")
        st.info("Open the **Upload** page, load both datasets, then run the merge to populate this report.")
        return

    df = get_all_data()
    if df is None or len(df) == 0:
        st.error("The report dataset could not be loaded.")
        return

    st.success(f"Dataset loaded: {len(df)} row(s), {len(df.columns)} column(s).")

    cols_info = get_available_columns(df)
    numeric_cols = cols_info["numeric"]
    categorical_cols = cols_info["categorical"]

    st.divider()

    # ═══ SECTION 1: FILTERS ═══
    st.subheader("Filters")

    col1, col2 = st.columns(2)

    # Date filter
    with col1:
        date_columns = [c for c in df.columns if "date" in c.lower()]

        if date_columns:
            date_col = st.selectbox("Date Column", date_columns, key="date_col_select")

            # Default window: the last 30 days
            default_start = date.today() - timedelta(days=30)
            default_end = date.today()

            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
                key="date_range_input",
            )
            use_date_filter = st.checkbox(
                "Apply date filter", value=False, key="use_date_filter"
            )
        else:
            date_col = None
            use_date_filter = False
            st.info("No date column was detected.")

    # Status filter
    with col2:
        if "_status" in df.columns:
            statuses = sorted(df["_status"].unique().tolist())
            selected_status = st.multiselect(
                "Status (Sold / No-Sale / Orphan)",
                options=statuses,
                default=statuses,
                key="status_filter",
            )
        else:
            selected_status = None

    # Apply filters
    filtered_df = df.copy()

    if use_date_filter and date_col and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        filtered_df = filter_by_date(filtered_df, date_col, date_range[0], date_range[1])

    if selected_status is not None and "_status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["_status"].isin(selected_status)]

    st.caption(f"Filtered records: **{len(filtered_df)}** of {len(df)} row(s).")

    st.divider()
# ═══ SECTION 2: CALCULATION ═══
    st.subheader("Custom Calculation")
    st.caption("Create a new column from Column A, an operation and Column B.")

    with st.expander("Add a calculated column", expanded=False):
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
            # Column B is only required for binary operations
            if operation in ("sum", "subtract", "multiply", "divide"):
                col_b = st.selectbox("Column B", numeric_cols, key="calc_col_b")
            else:
                col_b = None
                st.caption("(Column B is not required)")

        with c4:
            output_name = st.text_input(
                "Output Column Name", value="calculated", key="calc_output_name"
            )

        if st.button("Apply Calculation", key="apply_calc_btn"):
            try:
                filtered_df = apply_calculation(
                    filtered_df, col_a, operation, col_b, output_name
                )
                st.session_state["report_filtered_df"] = filtered_df
                st.success(f"Calculated column '{output_name}' added successfully.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001 — surfaced to the user
                st.error(f"Calculation failed: {exc}")

    # Restore a previously calculated column, if one is active
    if "report_filtered_df" in st.session_state and st.session_state["report_filtered_df"] is not None:
        filtered_df = st.session_state["report_filtered_df"]
        st.info(
            f"A calculated column is active — the dataset now has "
            f"{len(filtered_df.columns)} column(s)."
        )

        if st.button("Reset Calculated Columns", key="reset_calc_btn"):
            st.session_state["report_filtered_df"] = None
            st.rerun()

    st.divider()

    # ═══ SECTION 3: GROUP REPORT ═══
    st.subheader("Group Report")

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

    if st.button("Generate Report", type="primary", key="gen_report_btn"):
        try:
            report_df = generate_report(
                filtered_df,
                group_by=group_by,
                metric_col=metric_col,
                aggregation=aggregation,
            )

            if len(report_df) == 0:
                st.warning("The current filters returned no data.")
            else:
                st.subheader("Report Result")
                st.dataframe(report_df, use_container_width=True, hide_index=True)

                download_excel_button(
                    "Download Report (Excel)",
                    report_df,
                    f"report_{date.today()}.xlsx",
                    sheet_name="Report",
                )

                # Render a chart when the report is a simple two-column table
                if len(report_df.columns) == 2 and len(report_df) > 1:
                    chart_col = report_df.columns[1]
                    label_col = report_df.columns[0]
                    chart_data = report_df[report_df[label_col] != "TOTAL"]
                    if len(chart_data) > 0:
                        st.subheader("Chart")
                        st.bar_chart(chart_data.set_index(label_col)[chart_col])

        except Exception as exc:  # noqa: BLE001 — surfaced to the user
            st.error(f"Report generation failed: {exc}")

    st.divider()

    # ═══ SECTION 4: SUMMARY ═══
    st.subheader("Summary")

    # ─── Calls and records summary ───
    st.markdown("**Calls and records summary**")
    calls_summary = get_calls_summary(filtered_df)
    if len(calls_summary) > 0:
        st.dataframe(calls_summary, use_container_width=True, hide_index=True)

    st.divider()

    # ─── Numeric columns summary ───
    st.markdown("**Numeric columns summary**")
    st.caption("Identifier and phone-number columns are excluded automatically.")

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
            download_excel_button(
                "Download Summary (Excel)",
                summary_df,
                f"summary_{date.today()}.xlsx",
                sheet_name="Summary",
            )
        else:
            st.info("No valid numeric columns were found.")
    else:
        st.info("Select at least one column to build the summary.")

    # ═══ SECTION 5: RAW DATA PREVIEW ═══
    with st.expander("Filtered data preview (full)"):
        st.dataframe(filtered_df, use_container_width=True, height=400)
        download_excel_button(
            "Download Full Filtered Data (Excel)",
            filtered_df,
            f"filtered_data_{date.today()}.xlsx",
            sheet_name="Filtered Data",
        )