"""
results_page.py — Merge results view.

Displays the Sold / No-Sale / Orphan reconciliation produced by the merge.
"""

import streamlit as st

from app.utils import styles
from app.utils.caching import download_excel_button
from app.utils.session import has_result


def _render_dataset(container, df, sheet_name, file_name, caption, empty_message):
    """Render one dataset tab: caption, table, download button."""
    with container:
        st.caption(caption)
        if len(df) > 0:
            st.dataframe(df, use_container_width=True, height=400)
            download_excel_button(
                f"Download {sheet_name} (Excel)",
                df,
                file_name,
                sheet_name=sheet_name,
                use_container_width=True,
            )
        else:
            st.info(empty_message)


def render():
    """Render the merge results page."""
    styles.page_header(
        "Merge Results",
        "Sold, No-Sale and Orphan reconciliation",
        icon="📊",
    )

    if not has_result():
        st.warning("No merge results are available yet.")
        st.info("Open the **Upload** page, load both datasets, then run the merge to populate this report.")
        return

    result = st.session_state["merge_result"]
    summary = result["summary"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]

    # ═══ SUMMARY ═══
    with styles.card():
        st.subheader("Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sold (Matched)", summary["sold_rows"])
        c2.metric("No-Sale (Call Center only)", summary["no_sale_rows"])
        c3.metric("Orphan (Client only)", summary["orphan_rows"])

    st.divider()

    # ═══ DATASET TABS ═══
    tab_sold, tab_no_sale, tab_orphan = st.tabs([
        f"Sold ({len(sold)})",
        f"No-Sale ({len(no_sale)})",
        f"Orphan ({len(orphan)})",
    ])

    _render_dataset(
        tab_sold, sold, "Sold", "sold.xlsx",
        "Calls that resulted in a confirmed sale.",
        "No sold records are available.",
    )
    _render_dataset(
        tab_no_sale, no_sale, "No-Sale", "no_sale.xlsx",
        "Calls logged by the call center with no matching sale on the client side.",
        "No no-sale records are available.",
    )
    _render_dataset(
        tab_orphan, orphan, "Orphan", "orphan.xlsx",
        "Sales recorded on the client side with no matching call in the call center log.",
        "No orphan records are available.",
    )