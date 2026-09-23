"""
app.py - Main Entry Point
CallCenterTracker
"""

import streamlit as st
from app.config import get
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

# --- Page Setup ---
st.set_page_config(
    page_title=get("app.name", "CallCenterTracker"),
    page_icon=":telephone:",
    layout="wide",
)

# --- Session Init ---
init_session()

if "logout" not in st.session_state:
    st.session_state["logout"] = False
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "name" not in st.session_state:
    st.session_state["name"] = None

# Authenticator
authenticator = create_authenticator()

# --- Check Login ---
auth_status = st.session_state.get("authentication_status")

if not auth_status:
    login_page.render(authenticator)
    st.stop()

# --- Logged In ---
user = get_current_user()
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
    st.title("CallCenterTracker")
    st.caption(f"v{get('app.version')} - {get('app.environment')}")
    st.divider()

    st.markdown(f"User: **{user['name']}**")
    role_badge = "Master" if is_master_user else "User"
    st.caption(role_badge)

    st.divider()

    page = st.radio(
        "Navigation",
        nav_items,
        label_visibility="collapsed",
        key="main_nav_radio",
    )
    st.session_state["current_page"] = page

    st.divider()

    authenticator.logout("Logout", "sidebar", key="logout_btn")

    st.divider()
    st.caption("Auto-Fetch ready")
    st.caption("Phase 7 - Deployment aage aayega")

# --- Route to Page ---
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
