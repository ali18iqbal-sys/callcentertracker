"""
login_page.py — Login screen
Authenticator bahar se aata hai (app.py se).
"""

import streamlit as st


def render(authenticator):
    """Login screen dikhao"""
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        st.markdown(
            "<h1 style='text-align: center;'>📞</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h2 style='text-align: center;'>CallCenterTracker</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: gray;'>Sales Conversion Tracking System</p>",
            unsafe_allow_html=True,
        )
        
        st.divider()
        
        authenticator.login(
            location="main",
            fields={
                "Form name": "🔐 Login",
                "Username": "Username",
                "Password": "Password",
                "Login": "Login",
            },
        )
        
        auth_status = st.session_state.get("authentication_status")
        
        if auth_status is False:
            st.error("❌ Username ya password ghalat hai")
        elif auth_status is None:
            st.caption("Demo credentials: **admin / admin123**")