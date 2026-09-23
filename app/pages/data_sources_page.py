"""data_sources_page.py - Auto Data Sources UI"""

import streamlit as st
from app.core.sources_manager import load_sources, add_gsheet, add_api, delete_source
from app.core.gsheet_fetcher import fetch_gsheet
from app.core.api_fetcher import fetch_api


def add_to_session(df, source_type, source_name):
    key = f"{source_type}_dfs"
    files_key = f"{source_type}_files"
    if key not in st.session_state:
        st.session_state[key] = []
    if files_key not in st.session_state:
        st.session_state[files_key] = []
    df["_source_file"] = f"[Auto] {source_name}"
    st.session_state[key].append(df)
    st.session_state[files_key].append(f"[Auto] {source_name}")


def render():
    st.title("Auto Data Sources")
    st.caption("Google Sheet ya API se direct data fetch karein")
    st.divider()
    
    tab1, tab2 = st.tabs(["Google Sheets", "APIs"])
    with tab1:
        render_gsheets()
    with tab2:
        render_apis()
    
    st.divider()
    st.subheader("Currently Loaded Data")
    c1, c2 = st.columns(2)
    with c1:
        count = len(st.session_state.get("client_dfs", []))
        rows = sum(len(d) for d in st.session_state.get("client_dfs", []))
        st.metric("Client Data", f"{count} file(s)", f"{rows} rows")
    with c2:
        count = len(st.session_state.get("cc_dfs", []))
        rows = sum(len(d) for d in st.session_state.get("cc_dfs", []))
        st.metric("Call Center Data", f"{count} file(s)", f"{rows} rows")
    st.info("Fetch ke baad Upload page par jayein aur Merge button dabayein")


def render_gsheets():
    st.subheader("Google Sheet Sources")
    sources = load_sources()
    gsheets = sources.get("google_sheets", [])
    
    if gsheets:
        for i, src in enumerate(gsheets):
            with st.expander(f"{src['name']} - {src['type'].upper()}", expanded=False):
                st.write(f"URL: {src['url'][:80]}")
                st.write(f"Tab: {src.get('sheet_name') or '(default)'}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Fetch Now", key=f"gs_f_{i}", use_container_width=True):
                        fetch_gsheet_now(src)
                with c2:
                    if st.button("Delete", key=f"gs_d_{i}", use_container_width=True):
                        delete_source("google_sheets", i)
                        st.rerun()
    else:
        st.info("Koi Google Sheet source add nahi kiya")
    
    st.divider()
    with st.expander("Add Naya Google Sheet", expanded=False):
        with st.form("add_gsheet", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name", placeholder="Client Sales Feb")
                url = st.text_input("Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")
            with c2:
                source_type = st.selectbox("Data Type", ["client", "cc"],
                    format_func=lambda x: "Client (Sales)" if x == "client" else "Call Center (Calls)")
                sheet_name = st.text_input("Sheet Tab (optional)", placeholder="Sheet1")
                cred_file = st.text_input("Credentials Path", value="creds/service_account.json")
            
            if st.form_submit_button("Add Source", type="primary", use_container_width=True):
                if name and url:
                    add_gsheet(name, url, source_type, sheet_name, cred_file)
                    st.success(f"{name} add ho gaya")
                    st.rerun()
                else:
                    st.error("Name aur URL zaroori hain")
    
    with st.expander("Service Account Setup Guide"):
        st.markdown("""
### Google Service Account Setup

**Step 1** - https://console.cloud.google.com/ par jayein, naya project banayein

**Step 2** - APIs & Services > Library mein:
- Google Sheets API enable karein
- Google Drive API enable karein

**Step 3** - APIs & Services > Credentials > Create Credentials > Service Account

**Step 4** - Service account banao, phir Keys tab > Add Key > Create new key > JSON
- JSON file download karein
- Isay `creds/service_account.json` mein save karein

**Step 5** - Service account ka email copy karein
- Client ki Google Sheet kholein > Share
- Email add karein > Viewer access dein
- Done!
""")


def fetch_gsheet_now(src):
    try:
        with st.spinner(f"Fetching {src['name']}..."):
            df = fetch_gsheet(
                url=src["url"],
                credential_file=src["credential_file"],
                sheet_name=src.get("sheet_name") or None,
            )
            add_to_session(df, src["type"], src["name"])
            st.success(f"{len(df)} rows fetch hue")
            with st.expander("Preview"):
                st.dataframe(df.head(5), use_container_width=True)
    except FileNotFoundError:
        st.error(f"Credentials file nahi mili: {src['credential_file']}")
    except Exception as e:
        st.error(f"Error: {str(e)[:300]}")


def render_apis():
    st.subheader("API Sources")
    sources = load_sources()
    apis = sources.get("apis", [])
    
    if apis:
        for i, src in enumerate(apis):
            with st.expander(f"{src['name']} - {src['type'].upper()}", expanded=False):
                st.write(f"URL: {src['url'][:80]}")
                st.write(f"Auth: {src.get('auth_type', 'none')}")
                if src.get("json_path"):
                    st.write(f"JSON Path: {src['json_path']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Fetch Now", key=f"api_f_{i}", use_container_width=True):
                        fetch_api_now(src)
                with c2:
                    if st.button("Delete", key=f"api_d_{i}", use_container_width=True):
                        delete_source("apis", i)
                        st.rerun()
    else:
        st.info("Koi API source add nahi kiya")
    
    st.divider()
    with st.expander("Add Naya API Source", expanded=False):
        with st.form("add_api", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name", placeholder="Client API")
                url = st.text_input("Endpoint URL", placeholder="https://api.client.com/v1/sales")
                source_type = st.selectbox("Data Type", ["client", "cc"],
                    format_func=lambda x: "Client (Sales)" if x == "client" else "Call Center (Calls)",
                    key="api_type_form")
            with c2:
                auth_type = st.selectbox("Auth Type", ["none", "bearer", "api_key"],
                    format_func=lambda x: {"none": "No Auth", "bearer": "Bearer Token", "api_key": "API Key"}[x])
                auth_value = st.text_input("Token/Key", type="password", placeholder="xxxx")
                json_path = st.text_input("JSON Path (optional)", placeholder="data.items")
            
            if st.form_submit_button("Add Source", type="primary", use_container_width=True):
                if name and url:
                    add_api(name, url, source_type, auth_type, auth_value, json_path)
                    st.success(f"{name} add ho gaya")
                    st.rerun()
                else:
                    st.error("Name aur URL zaroori hain")
    
    with st.expander("Test API Example"):
        st.markdown("""
### Try karein with Free Test API

**Name:** Test API
**URL:** `https://jsonplaceholder.typicode.com/users`
**Data Type:** client
**Auth:** No Auth
**JSON Path:** (khali)

Add karein aur "Fetch Now" click karein - 10 rows aayengi.
""")


def fetch_api_now(src):
    try:
        with st.spinner(f"Fetching {src['name']}..."):
            df = fetch_api(
                url=src["url"],
                auth_type=src.get("auth_type", "none"),
                auth_value=src.get("auth_value"),
                json_path=src.get("json_path") or None,
            )
            add_to_session(df, src["type"], src["name"])
            st.success(f"{len(df)} rows fetch hue")
            with st.expander("Preview"):
                st.dataframe(df.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"Error: {str(e)[:300]}")
