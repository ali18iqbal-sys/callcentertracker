"""
missing_page.py — Missing and mismatch report.

Surfaces the records that did not reconcile between the two datasets.
"""

import streamlit as st

from app.utils import styles
from app.utils.caching import download_excel_button
from app.utils.session import has_result


def render():
    """Render the missing / mismatch report."""
    styles.page_header(
        "Missing / Mismatch",
        "Records that did not reconcile across the two datasets",
        icon="⚠️",
    )

    if not has_result():
        st.warning("No merge results are available yet.")
        st.info("Open the **Upload** page, load both datasets, then run the merge to populate this report.")
        return

    result = st.session_state["merge_result"]
    sold = result["sold"]
    no_sale = result["no_sale"]
    orphan = result["orphan"]

    st.caption("This report highlights where the client and call center datasets did not align.")

    # ═══ SUMMARY ═══
    c1, c2, c3 = st.columns(3)
    c1.metric("Sold (Matched)", len(sold))
    c2.metric("No-Sale (Call Center only)", len(no_sale))
    c3.metric("Orphan (Client only)", len(orphan))

    st.divider()

    # ═══ REPORT TABS ═══
    tab_orphan, tab_no_sale = st.tabs([
        f"Orphan Sales ({len(orphan)})",
        f"No-Sale Calls ({len(no_sale)})",
    ])

    # ─── ORPHAN SALES ───
    with tab_orphan:
        st.subheader("Orphan Sales")
        st.caption("Present in the client file but with no matching call in the call center log")

        if len(orphan) > 0:
            st.warning(
                f"**{len(orphan)}** phone number(s) appear in the client file but were not found in the call center file."
            )
            st.dataframe(orphan, use_container_width=True, height=400)
            download_excel_button(
                "Download Orphan Sales (Excel)",
                orphan,
                "orphan_sales.xlsx",
                sheet_name="Orphan",
                use_container_width=True,
            )
            st.info(
                """
**Common causes**
- The call center export is incomplete (one or more dialers are missing).
- Phone number formatting differs (normalisation is applied automatically).
- The client recorded an incorrect phone number.
"""
            )
        else:
            st.success("No orphan records — every client phone number was matched in the call center data.")

    # ─── NO-SALE CALLS ───
    with tab_no_sale:
        st.subheader("No-Sale Calls")
        st.caption("Logged by the call center, but with no corresponding sale on the client side")

        if len(no_sale) > 0:
            st.warning(f"**{len(no_sale)}** call(s) did not convert into a sale.")

            st.dataframe(no_sale, use_container_width=True, height=400)
            download_excel_button(
                "Download No-Sale Calls (Excel)",
                no_sale,
                "no_sale_calls.xlsx",
                sheet_name="No-Sale",
            )

            st.info(
                """
These records are valid activity: the call was placed, but it did not convert.
In the team and dialer performance views they appear as effort without a sale.
"""
            )
        else:
            st.success("No no-sale calls — every logged call converted into a sale.")