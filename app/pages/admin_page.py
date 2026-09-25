"""
admin_page.py — Master Panel (User Management)
Sirf Master role ke liye.
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


def render():
    """Master Panel page"""
    
    user = get_current_user()
    
    # Guard: sirf master access kar sakta hai
    if not user or user.get("role") != "master":
        st.error("❌ Only Master role users can access this page")
        st.stop()
    
    st.title("👑 Master Panel")
    st.caption("Manage users — add, edit, disable, change password")
    
    st.divider()
    
    # ═══ TABS ═══
    tab1, tab2, tab3 = st.tabs(["👥 Users", "➕ Add User", "🔑 Change Password"])
    
    # ─────────── TAB 1: USERS LIST ───────────
    with tab1:
        st.subheader("📋 User List")
        
        users = list_users()
        
        if users:
            df = pd.DataFrame(users)
            
            # Status column
            df["status"] = df["disabled"].apply(lambda x: "⏸️ Disabled" if x else "✅ Active")
            
            st.dataframe(
                df[["username", "name", "email", "role", "status"]],
                use_container_width=True,
                hide_index=True,
            )
            
            st.divider()
            st.subheader("⚙️ User Actions")
            
            # Select user
            usernames = [u["username"] for u in users]
            selected = st.selectbox("Choose user", usernames, key="user_actions_select")
            
            if selected:
                selected_info = next(u for u in users if u["username"] == selected)
                
                col1, col2, col3 = st.columns(3)
                
                # Toggle disable/enable
                with col1:
                    if selected_info["disabled"]:
                        if st.button("✅ Enable", key="enable_btn", use_container_width=True):
                            ok, msg = toggle_user_disabled(selected)
                            if ok:
                                st.success(msg)
                                st.rerun()
                    else:
                        if st.button("⏸️ Disable", key="disable_btn", use_container_width=True):
                            ok, msg = toggle_user_disabled(selected)
                            if ok:
                                st.success(msg)
                                st.rerun()
                
                # Edit role
                with col2:
                    new_role = st.selectbox(
                        "Change Role",
                        ["user", "master"],
                        index=0 if selected_info["role"] == "user" else 1,
                        key="role_change",
                    )
                    if new_role != selected_info["role"]:
                        if st.button("💾 Save Role", key="save_role", use_container_width=True):
                            ok, msg = update_user(selected, role=new_role)
                            if ok:
                                st.success(msg)
                                st.rerun()
                
                # Delete user
                with col3:
                    if selected != "admin":
                        if st.button("🗑️ Delete", key="delete_btn", use_container_width=True):
                            ok, msg = delete_user(selected)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.caption("((admin cannot be deleted))")
        else:
            st.info("No users found")
    
    # ─────────── TAB 2: ADD USER ───────────
    with tab2:
        st.subheader("➕ Add New User")
        
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username *", placeholder="jaise: ahmed")
                new_name = st.text_input("Full Name", placeholder="Ahmed Khan")
            
            with col2:
                new_email = st.text_input("Email", placeholder="ahmed@callcenter.local")
                new_role = st.selectbox("Role", ["user", "master"], index=0)
            
            new_password = st.text_input("Password *", type="password", placeholder="min 6 characters")
            new_password_confirm = st.text_input("Confirm Password *", type="password")
            
            submit = st.form_submit_button("💾 Add User", type="primary", use_container_width=True)
            
            if submit:
                # Validation
                if not new_username or not new_password:
                    st.error("❌ Username and Password are required")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif new_password != new_password_confirm:
                    st.error("❌ Passwords do not match")
                elif " " in new_username:
                    st.error("❌ Username cannot contain spaces")
                else:
                    ok, msg = add_user(
                        username=new_username.strip().lower(),
                        name=new_name.strip(),
                        email=new_email.strip(),
                        password=new_password,
                        role=new_role,
                    )
                    if ok:
                        st.success(f"✅ {msg}")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg}")
    
    # ─────────── TAB 3: CHANGE PASSWORD ───────────
    with tab3:
        st.subheader("🔑 Change Password")
        
        users = list_users()
        usernames = [u["username"] for u in users]
        
        selected_pw_user = st.selectbox("Choose user", usernames, key="pw_change_select")
        
        with st.form("change_pw_form", clear_on_submit=True):
            new_pw = st.text_input("New Password *", type="password")
            new_pw_confirm = st.text_input("Confirm New Password *", type="password")
            
            submit_pw = st.form_submit_button("💾 Change Password", type="primary", use_container_width=True)
            
            if submit_pw:
                if not new_pw:
                    st.error("❌ Password is required")
                elif len(new_pw) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif new_pw != new_pw_confirm:
                    st.error("❌ Passwords do not match")
                else:
                    ok, msg = change_password(selected_pw_user, new_pw)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")