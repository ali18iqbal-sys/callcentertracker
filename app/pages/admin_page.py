"""
admin_page.py — Master panel (user administration).

Restricted to users holding the Master role.
"""

import streamlit as st
import pandas as pd
from app.core.auth import (
    list_users,
    add_user,
    update_user,
    change_password,
    toggle_user_disabled,
    delete_user,
    get_current_user,
)
from app.utils import styles


def render():
    """Render the Master Panel page."""

    user = get_current_user()

    # Access control: only the Master role may open this page
    if not user or user.get("role") != "master":
        st.error("This page is restricted to users with the Master role.")
        st.stop()

    styles.page_header(
        "Master Panel",
        "Manage users — add, edit, disable accounts and reset passwords",
        icon="👑",
    )

    st.divider()

    # ═══ TABS ═══
    tab_users, tab_add, tab_password = st.tabs(["Users", "Add User", "Change Password"])

    # ─────────── TAB 1: USERS LIST ───────────
    with tab_users:
        st.subheader("User List")
        
        users = list_users()
        
        if users:
            df = pd.DataFrame(users)
            df["status"] = df["disabled"].apply(lambda x: "Disabled" if x else "Active")

            st.dataframe(
                df[["username", "name", "email", "role", "status"]],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("User Actions")

            usernames = [u["username"] for u in users]
            selected = st.selectbox("Select a user", usernames, key="user_actions_select")

            if selected:
                selected_info = next(u for u in users if u["username"] == selected)

                col1, col2, col3 = st.columns(3)

                # Enable or disable the account
                with col1:
                    action = "Enable" if selected_info["disabled"] else "Disable"
                    key = "enable_btn" if selected_info["disabled"] else "disable_btn"
                    if st.button(action, key=key, use_container_width=True):
                        ok, msg = toggle_user_disabled(selected)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                # Change the role
                with col2:
                    new_role = st.selectbox(
                        "Change Role",
                        ["user", "master"],
                        index=0 if selected_info["role"] == "user" else 1,
                        key="role_change",
                    )
                    if new_role != selected_info["role"]:
                        if st.button("Save Role", key="save_role", use_container_width=True):
                            ok, msg = update_user(selected, role=new_role)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                # Delete the account
                with col3:
                    if selected != "admin":
                        if st.button("Delete", key="delete_btn", use_container_width=True):
                            ok, msg = delete_user(selected)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.caption("The admin account cannot be deleted.")
        else:
            st.info("No users are configured.")

    # ─────────── TAB 2: ADD USER ───────────
    with tab_add:
        st.subheader("Add New User")
        
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username *", placeholder="e.g. j.smith")
                new_name = st.text_input("Full Name", placeholder="Jane Smith")

            with col2:
                new_email = st.text_input("Email", placeholder="jane.smith@company.com")
                new_role = st.selectbox("Role", ["user", "master"], index=0)

            new_password = st.text_input("Password *", type="password", placeholder="Minimum 6 characters")
            new_password_confirm = st.text_input("Confirm Password *", type="password")

            submit = st.form_submit_button("Add User", type="primary", use_container_width=True)

            if submit:
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                elif len(new_password) < 6:
                    st.error("The password must be at least 6 characters long.")
                elif new_password != new_password_confirm:
                    st.error("The passwords do not match.")
                elif " " in new_username:
                    st.error("The username cannot contain spaces.")
                else:
                    ok, msg = add_user(
                        username=new_username.strip().lower(),
                        name=new_name.strip(),
                        email=new_email.strip(),
                        password=new_password,
                        role=new_role,
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    # ─────────── TAB 3: CHANGE PASSWORD ───────────
    with tab_password:
        st.subheader("Change Password")

        users = list_users()
        usernames = [u["username"] for u in users]

        selected_pw_user = st.selectbox("Select a user", usernames, key="pw_change_select")

        with st.form("change_pw_form", clear_on_submit=True):
            new_pw = st.text_input("New Password *", type="password")
            new_pw_confirm = st.text_input("Confirm New Password *", type="password")

            submit_pw = st.form_submit_button(
                "Change Password", type="primary", use_container_width=True
            )

            if submit_pw:
                if not new_pw:
                    st.error("A password is required.")
                elif len(new_pw) < 6:
                    st.error("The password must be at least 6 characters long.")
                elif new_pw != new_pw_confirm:
                    st.error("The passwords do not match.")
                else:
                    ok, msg = change_password(selected_pw_user, new_pw)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)