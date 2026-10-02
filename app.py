"""
app.py — Main entry point for CallCenterTracker.

Responsibilities:
    1. Page configuration and global theming
    2. Session bootstrap
    3. Authentication gate
    4. Sidebar navigation and page routing
"""

import streamlit as st

from app.config import get
from app.utils import styles
from app.utils.session import init_session
from app.core.auth import create_authenticator, get_current_user, is_master
from app.pages import (
    login_page,
    upload_page,
    results_page,
    performance_page,
    missing_page,
    admin_page,
    target_page,
    report_page,
    data_sources_page,
)


# --- Page configuration ---
st.set_page_config(
    page_title=get("app.name", "CallCenterTracker"),
    page_icon="📞",
    layout="wide",
)

# --- Global theme (light corporate SaaS) ---
styles.inject_global_css()

# --- Session bootstrap ---
init_session()

for _key, _default in (
    ("logout", False),
    ("authentication_status", None),
    ("username", None),
    ("name", None),
):
    if _key not in st.session_state:
        st.session_state[_key] = _default

# --- Authenticator ---
try:
    authenticator = create_authenticator()
except Exception as exc:  # noqa: BLE001 — configuration / secrets problems
    st.error(
        "Authentication configuration could not be loaded. Verify that "
        "`users.yaml` exists in the project root for local development, or that "
        "a `users` section is configured in Streamlit Secrets."
    )
    st.exception(exc)
    st.stop()

# --- Authentication gate ---
if not st.session_state.get("authentication_status"):
    login_page.render(authenticator)
    st.stop()

# --- Authenticated user ---
user = get_current_user()
if user is None:
    # An authenticated status without a matching user record means the session
    # is no longer valid — request a fresh sign-in instead of failing later.
    st.session_state["authentication_status"] = None
    st.session_state["username"] = None
    st.session_state["name"] = None
    st.warning("Your session has expired or is no longer valid. Please sign in again.")
    st.stop()

is_master_user = is_master()

nav_items = [
    "Upload",
    "Data Sources",
    "Results",
    "Performance",
    "Missing",
    "Targets",
    "Reports",
]
if is_master_user:
    nav_items.append("Master Panel")

with st.sidebar:
    version = str(get("app.version", "") or "")
    environment = str(get("app.environment", "") or "").title()
    styles.brand_block(
        get("app.name", "CallCenterTracker"),
        f"Version {version} · {environment}" if version else environment,
    )

    styles.user_card(user["name"], "master" if is_master_user else "user")

    st.divider()

    page = st.radio(
        "Navigation",
        nav_items,
        label_visibility="collapsed",
        key="main_nav_radio",
    )
    st.session_state["current_page"] = page

    st.divider()

    authenticator.logout("Sign out", "sidebar", key="logout_btn")

    st.divider()
    st.caption("Auto-fetch scheduler available")
    st.caption("All data is processed locally in your session")

# --- Page routing ---
if page == "Upload":
    upload_page.render()
elif page == "Data Sources":
    data_sources_page.render()
elif page == "Results":
    results_page.render()
elif page == "Performance":
    performance_page.render()
elif page == "Missing":
    missing_page.render()
elif page == "Targets":
    target_page.render()
elif page == "Reports":
    report_page.render()
elif page == "Master Panel":
    admin_page.render()