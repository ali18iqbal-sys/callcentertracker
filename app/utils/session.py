"""
session.py — Session state helpers
Multiple files support ke saath.
"""

import streamlit as st
import pandas as pd


def init_session():
    defaults = {
        "client_dfs": [],
        "cc_dfs": [],
        "client_files": [],
        "cc_files": [],
        "merge_result": None,
        "current_page": "Upload",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_data():
    st.session_state["client_dfs"] = []
    st.session_state["cc_dfs"] = []
    st.session_state["client_files"] = []
    st.session_state["cc_files"] = []
    st.session_state["merge_result"] = None


def has_both_files():
    return (len(st.session_state["client_dfs"]) > 0 and 
            len(st.session_state["cc_dfs"]) > 0)


def has_result():
    return st.session_state["merge_result"] is not None


def get_combined_client():
    dfs = st.session_state["client_dfs"]
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True, sort=False)


def get_combined_cc():
    dfs = st.session_state["cc_dfs"]
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True, sort=False)