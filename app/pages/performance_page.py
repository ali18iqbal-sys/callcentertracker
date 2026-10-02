"""
performance_page.py — Team and dialer performance dashboard.

Every metric is defensive: missing columns are handled gracefully and the page
never fails because a source file lacks an expected field.
"""

import pandas as pd
import streamlit as st

from app.utils import styles
from app.utils.caching import (
    dialer_metrics,
    download_excel_button,
    summary_stats,
    team_metrics,
)
from app.utils.session import has_result


_COLUMN_CONFIG = {
    "calls": st.column_config.NumberColumn("Calls", format="%d"),
    "sales": st.column_config.NumberColumn("Sales", format="%d"),
    "conversion_pct": st.column_config.NumberColumn("Conversion %", format="%.2f%%"),
    "amount": st.column_config.NumberColumn("Amount", format="%,.0f"),
}


def render():
    """Render the performance dashboard."""
    styles.page_header(
        "Performance",
        "Team and dialer conversion insights",
        icon="🚀",
    )

    if not has_result():
        st.warning("No merge results are available yet.")
        st.info("Open the **Upload** page, load both datasets, then run the merge to populate this dashboard.")
        return

    result = st.session_state["merge_result"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]

    # ═══ OVERALL STATISTICS ═══
    try:
        stats = summary_stats(sold, no_sale, orphan)
        with styles.card():
            st.subheader("Overall Performance")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Calls", f"{stats['total_calls']:,}")
            c2.metric("Sales", f"{stats['total_sales']:,}")
            c3.metric("Conversion", f"{stats['conversion_pct']}%")
            c4.metric("Total Amount", f"{stats['total_amount']:,.0f}")
    except Exception as exc:  # noqa: BLE001 — surfaced to the user
        st.error(f"Overall statistics could not be calculated: {exc}")

    st.divider()

    # ═══ TEAM / DIALER TABS ═══
    tab_team, tab_dialer = st.tabs(["Team-wise", "Dialer-wise"])

    # ─── TEAM ───
    with tab_team:
        try:
            team_df = team_metrics(sold, no_sale)
        except Exception as exc:  # noqa: BLE001 — surfaced to the user
            st.error(f"Team performance could not be calculated: {exc}")
            team_df = pd.DataFrame()

        if len(team_df) > 0:
            st.caption("Team-wise performance (sorted by amount)")
            st.dataframe(
                team_df,
                use_container_width=True,
                height=400,
                column_config={"team": "Team", **_COLUMN_CONFIG},
            )

            try:
                st.subheader("Conversion by Team")
                st.bar_chart(team_df[["team", "conversion_pct"]].set_index("team"))
            except Exception:  # noqa: BLE001 — charts are best effort
                pass

            download_excel_button(
                "Download Team Performance (Excel)",
                team_df,
                "team_performance.xlsx",
                sheet_name="Performance",
            )
        else:
            st.warning("No team data is available.")
            st.info("Verify that the call center file contains a **Team** column.")

    # ─── DIALER ───
    with tab_dialer:
        try:
            dialer_df = dialer_metrics(sold, no_sale)
        except Exception as exc:  # noqa: BLE001 — surfaced to the user
            st.error(f"Dialer performance could not be calculated: {exc}")
            dialer_df = pd.DataFrame()

        if len(dialer_df) > 0:
            st.caption("Dialer-wise performance (sorted by amount)")
            st.dataframe(
                dialer_df,
                use_container_width=True,
                height=400,
                column_config={"dialer": "Dialer", **_COLUMN_CONFIG},
            )

            try:
                st.subheader("Amount by Dialer")
                st.bar_chart(dialer_df[["dialer", "amount"]].set_index("dialer"))
            except Exception:  # noqa: BLE001 — charts are best effort
                pass

            download_excel_button(
                "Download Dialer Performance (Excel)",
                dialer_df,
                "dialer_performance.xlsx",
                sheet_name="Performance",
            )
        else:
            st.warning("No dialer data is available.")
            st.info("Verify that the call center file contains a **Dialer** column.")