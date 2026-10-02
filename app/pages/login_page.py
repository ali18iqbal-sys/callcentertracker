"""
login_page.py — Sign-in screen.

The authenticator instance is created in app.py and passed in.
"""

import streamlit as st

from app.utils import styles


def render(authenticator):
    """Render the sign-in screen."""

    col1, col2, col3 = st.columns([1, 1.25, 1])

    with col2:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

        with styles.card():
            styles.login_hero(
                "CallCenterTracker",
                "Sales Conversion Tracking System",
            )

            st.divider()

            authenticator.login(
                location="main",
                fields={
                    "Form name": "Sign in",
                    "Username": "Username",
                    "Password": "Password",
                    "Login": "Sign in",
                },
            )

            auth_status = st.session_state.get("authentication_status")

            if auth_status is False:
                st.error("Invalid username or password. Please verify your credentials and try again.")
            elif auth_status is None:
                st.caption("Access is restricted to authorised users. Contact your administrator if you require an account.")