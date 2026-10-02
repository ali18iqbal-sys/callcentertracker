"""
session.py — Session state helpers.

Uploaded datasets are held per session and combined lazily: the concatenated
frame is memoised against the identity of its source frames, so switching pages
never re-concatenates the same files.

Note:
    The frames returned by :func:`get_combined_client` / :func:`get_combined_cc`
    are shared with the session. Callers that modify data must work on a copy.
"""

import pandas as pd
import streamlit as st


_CLIENT_KEY = "client"
_CC_KEY = "cc"


def init_session():
    """Initialise session defaults without overwriting existing state."""
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
            st.session_state[key] = list(value) if isinstance(value, list) else value


def clear_data():
    """Discard all uploaded datasets and cached combinations."""
    st.session_state["client_dfs"] = []
    st.session_state["cc_dfs"] = []
    st.session_state["client_files"] = []
    st.session_state["cc_files"] = []
    st.session_state["merge_result"] = None
    for side in (_CLIENT_KEY, _CC_KEY):
        st.session_state.pop(f"_combined_{side}", None)


def has_both_files():
    """True when at least one client file and one call center file are loaded."""
    return (
        len(st.session_state.get("client_dfs") or []) > 0
        and len(st.session_state.get("cc_dfs") or []) > 0
    )


def has_result():
    """True when a merge result is available."""
    return st.session_state.get("merge_result") is not None


def _combined(side):
    """Concatenate one side's frames, memoised for the session."""
    frames = st.session_state.get(f"{side}_dfs") or []
    cache_key = f"_combined_{side}"

    if not frames:
        st.session_state.pop(cache_key, None)
        return None

    signature = tuple(id(frame) for frame in frames)
    cached = st.session_state.get(cache_key)
    if cached is not None and cached[0] == signature:
        return cached[1]

    combined = pd.concat(frames, ignore_index=True, sort=False)
    st.session_state[cache_key] = (signature, combined)
    return combined


def get_combined_client():
    """Combined client dataset, or None when nothing is loaded."""
    return _combined(_CLIENT_KEY)


def get_combined_cc():
    """Combined call center dataset, or None when nothing is loaded."""
    return _combined(_CC_KEY)