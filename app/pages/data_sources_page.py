"""
data_sources_page.py — Automated data source management.

Covers Google Sheets, generic HTTP APIs and Ringba, together with the
auto-fetch timer used to refresh them on a schedule.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.core.sources_manager import (
    add_api,
    add_gsheet,
    add_ringba,
    delete_source,
    load_sources,
    resolve_ringba_credentials,
    toggle_source,
)
from app.core.gsheet_fetcher import fetch_gsheet
from app.core.api_fetcher import fetch_api
from app.core.ringba_fetcher import RingbaError, fetch_ringba_calls, normalize_ringba
from app.core import scheduler
from app.utils import styles
from app.utils.secrets import mask_secret


def add_to_session(df, source_type, source_name):
    """Add a fetched dataset to the session for the given side."""
    key = f"{source_type}_dfs"
    files_key = f"{source_type}_files"
    if key not in st.session_state:
        st.session_state[key] = []
    if files_key not in st.session_state:
        st.session_state[files_key] = []

    df = df.copy()
    df["_source_file"] = f"[Auto] {source_name}"
    st.session_state[key].append(df)
    st.session_state[files_key].append(f"[Auto] {source_name}")


def render():
    """Render the data sources page."""
    styles.page_header(
        "Auto Data Sources",
        "Fetch data directly from Google Sheets, an API or Ringba — with a configurable timer",
        icon="🔄",
    )
    st.divider()

    tab_gsheets, tab_apis, tab_ringba, tab_schedule = st.tabs(
        ["Google Sheets", "APIs", "Ringba", "Schedule"]
    )
    with tab_gsheets:
        render_gsheets()
    with tab_apis:
        render_apis()
    with tab_ringba:
        render_ringba()
    with tab_schedule:
        render_schedule()

    st.divider()
    with styles.card():
        st.subheader("Currently Loaded Data")
        c1, c2 = st.columns(2)
        with c1:
            frames = st.session_state.get("client_dfs", [])
            st.metric(
                "Client Data",
                f"{len(frames)} file(s)",
                f"{sum(len(d) for d in frames)} row(s)",
            )
        with c2:
            frames = st.session_state.get("cc_dfs", [])
            st.metric(
                "Call Center Data",
                f"{len(frames)} file(s)",
                f"{sum(len(d) for d in frames)} row(s)",
            )
    st.info("Once the data is fetched, open the **Upload** page and run the merge.")
# ═══════════════════════════════════════════════════════════
#  GOOGLE SHEETS
# ═══════════════════════════════════════════════════════════
def render_gsheets():
    """Render the Google Sheets source tab."""
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
        st.info("No Google Sheet source has been configured.")

    st.divider()
    with st.expander("Add New Google Sheet", expanded=False):
        with st.form("add_gsheet", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name", placeholder="Client Sales — February")
                url = st.text_input("Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")
            with c2:
                source_type = st.selectbox(
                    "Data Type", ["client", "cc"],
                    format_func=lambda x: "Client (Sales)" if x == "client" else "Call Center (Calls)",
                )
                sheet_name = st.text_input("Sheet Tab (optional)", placeholder="Sheet1")
                cred_file = st.text_input(
                    "Credentials Path",
                    value="creds/service_account.json",
                    help="Leave as default, or set GOOGLE_APPLICATION_CREDENTIALS in your environment.",
                )

            if st.form_submit_button("Add Source", type="primary", use_container_width=True):
                if name and url:
                    add_gsheet(name, url, source_type, sheet_name, cred_file)
                    st.success(f"Source '{name}' was added successfully.")
                    st.rerun()
                else:
                    st.error("Name and URL are required.")

    with st.expander("Service Account Setup Guide"):
        st.markdown("""
### Google Service Account Setup

**Step 1** — Open https://console.cloud.google.com/ and create a new project.

**Step 2** — Under *APIs & Services → Library*, enable:
- Google Sheets API
- Google Drive API

**Step 3** — Go to *APIs & Services → Credentials → Create Credentials → Service Account*.

**Step 4** — Create the service account, then open the *Keys* tab, choose
*Add Key → Create new key → JSON* and download the file.
- Store it at `creds/service_account.json` (this folder is git-ignored), or
  point `GOOGLE_APPLICATION_CREDENTIALS` at the file instead.

**Step 5** — Copy the service account email address.
- Open the client's Google Sheet and choose *Share*
- Add the email address with **Viewer** access

The source is then ready to fetch.
""")


def fetch_gsheet_now(src):
    """Fetch a Google Sheet source immediately and load it into the session."""
    try:
        with st.spinner(f"Fetching {src['name']}…"):
            df = fetch_gsheet(
                url=src["url"],
                credential_file=src.get("credential_file"),
                sheet_name=src.get("sheet_name") or None,
            )
            add_to_session(df, src["type"], src["name"])
            st.success(f"Fetched {len(df)} row(s).")
            with st.expander("Preview"):
                st.dataframe(df.head(5), use_container_width=True)
    except FileNotFoundError:
        st.error(
            f"The service account credentials file was not found: {src.get('credential_file')}. "
            "Update the credentials path, or set GOOGLE_APPLICATION_CREDENTIALS."
        )
    except Exception as exc:  # noqa: BLE001 — surfaced to the user
        st.error(f"Fetch failed: {str(exc)[:300]}")


# ═══════════════════════════════════════════════════════════
#  GENERIC APIs
# ═══════════════════════════════════════════════════════════
def render_apis():
    """Render the generic API source tab."""
    st.subheader("API Sources")
    sources = load_sources()
    apis = sources.get("apis", [])

    if apis:
        for i, src in enumerate(apis):
            with st.expander(f"{src['name']} - {src['type'].upper()}", expanded=False):
                st.write(f"URL: {src['url'][:80]}")
                st.write(f"Authentication: {src.get('auth_type', 'none')}")
                st.write(f"Credential: {mask_secret(src.get('auth_value'))}")
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
        st.info("No API source has been configured.")

    st.divider()
    with st.expander("Add New API Source", expanded=False):
        with st.form("add_api", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name", placeholder="Client Sales API")
                url = st.text_input("Endpoint URL", placeholder="https://api.client.com/v1/sales")
                source_type = st.selectbox(
                    "Data Type", ["client", "cc"],
                    format_func=lambda x: "Client (Sales)" if x == "client" else "Call Center (Calls)",
                    key="api_type_form",
                )
            with c2:
                auth_type = st.selectbox(
                    "Auth Type", ["none", "bearer", "api_key"],
                    format_func=lambda x: {"none": "No Authentication", "bearer": "Bearer Token", "api_key": "API Key"}[x],
                )
                auth_value = st.text_input(
                    "Token / Key",
                    type="password",
                    placeholder="Optional — resolved from the environment if left blank",
                    help="Leave blank to use API_TOKEN or API_KEY from your environment.",
                )
                json_path = st.text_input("JSON Path (optional)", placeholder="data.items")

            if st.form_submit_button("Add Source", type="primary", use_container_width=True):
                if name and url:
                    add_api(name, url, source_type, auth_type, auth_value, json_path)
                    st.success(f"Source '{name}' was added successfully.")
                    st.rerun()
                else:
                    st.error("Name and URL are required.")

    with st.expander("Test API Example"):
        st.markdown("""
### Try it with a public test API

- **Name:** Test API
- **URL:** `https://jsonplaceholder.typicode.com/users`
- **Data Type:** client
- **Authentication:** No Authentication
- **JSON Path:** (leave blank)

Add the source and select "Fetch Now" — 10 rows are returned.
""")


def fetch_api_now(src):
    """Fetch an API source immediately and load it into the session."""
    try:
        with st.spinner(f"Fetching {src['name']}…"):
            df = fetch_api(
                url=src["url"],
                auth_type=src.get("auth_type", "none"),
                auth_value=src.get("auth_value"),
                json_path=src.get("json_path") or None,
            )
            add_to_session(df, src["type"], src["name"])
            st.success(f"Fetched {len(df)} row(s).")
            with st.expander("Preview"):
                st.dataframe(df.head(5), use_container_width=True)
    except Exception as exc:  # noqa: BLE001 — surfaced to the user
        st.error(f"Fetch failed: {str(exc)[:300]}")
# ═══════════════════════════════════════════════════════════
#  RINGBA
# ═══════════════════════════════════════════════════════════
def render_ringba():
    """Render the Ringba source tab."""
    st.subheader("Ringba Sources")
    st.caption(
        "Ringba API v2 — call logs are fetched automatically using the "
        "`Authorization: Token` header."
    )

    sources = load_sources()
    ringba = sources.get("ringba", [])

    if ringba:
        for i, src in enumerate(ringba):
            enabled = src.get("enabled", True)
            status = "enabled" if enabled else "disabled"
            account_id, api_token = resolve_ringba_credentials(src)
            credential_source = (
                "source configuration" if src.get("api_token") else "environment / Streamlit Secrets"
            )

            with st.expander(
                f"{src['name']} — {str(src.get('data_type', 'cc')).upper()} ({status})",
                expanded=False,
            ):
                st.write(f"Account ID: `{account_id or '(not configured)'}`")
                st.write(f"API token: {mask_secret(api_token)}")
                st.write(f"Credential source: {credential_source}")
                st.write(f"Report window: last {src.get('report_days', 1)} day(s)")

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Fetch Now", key=f"rb_f_{i}", use_container_width=True):
                        fetch_ringba_now(src)
                with c2:
                    label = "Disable" if enabled else "Enable"
                    if st.button(label, key=f"rb_t_{i}", use_container_width=True):
                        toggle_source("ringba", i)
                        st.rerun()
                with c3:
                    if st.button("Delete", key=f"rb_d_{i}", use_container_width=True):
                        delete_source("ringba", i)
                        st.rerun()
    else:
        st.info("No Ringba source has been configured.")

    st.divider()
    with st.expander("Add Ringba Source", expanded=False):
        with st.form("add_ringba", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name", placeholder="Ringba — Primary")
                account_id = st.text_input(
                    "Account ID",
                    placeholder="ABC123…",
                    help="Optional when RINGBA_ACCOUNT_ID is set in the environment.",
                )
            with c2:
                api_token = st.text_input(
                    "API Token",
                    type="password",
                    placeholder="Optional — resolved from the environment if left blank",
                    help=(
                        "For security, leave this blank and set RINGBA_API_TOKEN in .env "
                        "or Streamlit Secrets instead of storing the token here."
                    ),
                )
                data_type = st.selectbox(
                    "Data Type", ["cc", "client"],
                    format_func=lambda x: "Call Center (Calls)" if x == "cc" else "Client (Sales)",
                )
                report_days = st.number_input(
                    "Report window (days back)", min_value=0, max_value=90,
                    value=1, step=1)

            if st.form_submit_button("Add Ringba Source", type="primary", use_container_width=True):
                if name and (account_id or api_token):
                    add_ringba(name, account_id, api_token, data_type, int(report_days), True)
                    st.success(f"Source '{name}' was added successfully.")
                    st.rerun()
                else:
                    st.error("Name is required, together with an Account ID or an API Token.")

    with st.expander("Ringba Setup Notes"):
        st.markdown("""
**Ringba API v2**
- Base URL: `https://api.ringba.com/v2`
- Endpoint used: `POST /{accountId}/calllogs`
- Authentication header: `Authorization: Token <api_token>`

**Where the credentials are found**
- API token: Ringba dashboard → Account → API / Integrations → API Token
- Account ID: displayed in the Ringba account URL or in the settings page

**Storing credentials securely**
- Prefer setting `RINGBA_ACCOUNT_ID` and `RINGBA_API_TOKEN` in a local `.env`
  file (see `.env.example`) or in Streamlit Secrets. The token field can then be
  left blank, and the value never has to be stored in `data/sources.yaml`.

**Report window** — each fetch sends `reportStart = today - days` and
`reportEnd = today`. Pagination is handled automatically.
""")


def fetch_ringba_now(src):
    """Fetch a Ringba source immediately and load it into the session."""
    days = int(src.get("report_days", 1) or 1)
    today = date.today()
    start = today - timedelta(days=days)

    try:
        account_id, api_token = resolve_ringba_credentials(src)

        with st.spinner(f"Fetching {src['name']} from Ringba…"):
            raw = fetch_ringba_calls(
                account_id=account_id,
                api_token=api_token,
                report_start=start,
                report_end=today,
            )
            df = normalize_ringba(raw)
            add_to_session(df, src.get("data_type", "cc"), src["name"])
            st.success(f"Fetched {len(df)} call record(s) ({start} → {today}).")
            with st.expander("Preview"):
                st.dataframe(df.head(5), use_container_width=True)
    except RingbaError as exc:
        st.error(f"Ringba request failed: {exc}")
    except Exception as exc:  # noqa: BLE001 — surfaced to the user
        st.error(f"Fetch failed: {str(exc)[:300]}")
# ═══════════════════════════════════════════════════════════
#  SCHEDULE / TIMER
# ═══════════════════════════════════════════════════════════
def _all_source_names():
    """Return the names of every configured source (used by the filter)."""
    s = load_sources()
    names = []
    for kind in ("google_sheets", "apis", "ringba"):
        names += [x.get("name") for x in s.get(kind, []) if x.get("name")]
    return names


def _render_job_outcome(outcome):
    """Display the outcome of an auto-fetch job."""
    st.success(
        f"Fetch completed — client: {outcome['client_rows']} row(s), "
        f"call center: {outcome['cc_rows']} row(s)."
    )
    if outcome.get("results"):
        st.dataframe(pd.DataFrame(outcome["results"]),
                     use_container_width=True, hide_index=True)
    if outcome.get("saved"):
        for kind, path in outcome["saved"].items():
            st.caption(f"Saved {kind} → {path}")


def render_schedule():
    """Render the auto-fetch timer tab."""
    st.subheader("Auto-Fetch Timer")
    st.caption(
        "Configure when the automatic fetch runs — either at a fixed interval "
        "or at specific times of day."
    )

    schedule = scheduler.load_schedule()
    last_run = scheduler.get_last_run()
    nxt = scheduler.next_run_time(schedule)
    state = scheduler.get_state()

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", "Enabled" if schedule.get("enabled") else "Disabled")
    c2.metric("Last run", last_run.strftime("%Y-%m-%d %H:%M") if last_run else "Never")
    c3.metric("Next run", nxt.strftime("%Y-%m-%d %H:%M") if nxt else "—")

    if scheduler.is_due(schedule):
        st.warning("A fetch is due — select **Run due now**, or start the background daemon.")
    else:
        st.success("No fetch is currently due.")

    st.divider()

    # ─── Configuration form ───
    with st.form("schedule_form"):
        enabled = st.checkbox("Enable auto-fetch", value=bool(schedule.get("enabled")))
        mode = st.radio(
            "Mode", ["interval", "times"],
            index=0 if schedule.get("mode") == "interval" else 1,
            format_func=lambda x: ("Interval (every N minutes)"
                                   if x == "interval" else "Specific times"),
        )
        interval_minutes = st.number_input(
            "Interval (minutes)", min_value=1, max_value=1440,
            value=int(schedule.get("interval_minutes", 60)), step=5)
        times_str = st.text_input(
            "Execution Times (24-hour clock, comma separated)",
            value=", ".join(schedule.get("times", [])) or "09:00, 13:00, 18:00",
            help="Used when the mode is set to Specific times.")
        run_on_start = st.checkbox(
            "Run once on start if it has never run before",
            value=bool(schedule.get("run_on_start", True)))
        persist = st.checkbox(
            "Save fetched data to data/fetched/",
            value=bool(schedule.get("persist_to_disk", True)))
        options = _all_source_names()
        sources_sel = st.multiselect(
            "Limit to specific sources (empty = all enabled sources)",
            options=options,
            default=[s for s in schedule.get("sources", []) if s in options],
        )
        saved = st.form_submit_button("Save Schedule", type="primary",
                                      use_container_width=True)

    if saved:
        times = [t.strip() for t in times_str.split(",") if t.strip()]
        new_sched = {
            "enabled": bool(enabled),
            "mode": mode,
            "interval_minutes": int(interval_minutes),
            "times": times,
            "sources": sources_sel,
            "run_on_start": bool(run_on_start),
            "persist_to_disk": bool(persist),
        }
        scheduler.save_schedule(new_sched)
        st.success("Schedule saved successfully.")
        st.rerun()

    st.divider()

    # ─── Manual triggers ───
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Run due now", use_container_width=True):
            outcome = scheduler.maybe_run_due()
            if outcome is None:
                st.info("No fetch was due at this time.")
            else:
                _render_job_outcome(outcome)
    with c2:
        if st.button("Force fetch now (ignore schedule)", use_container_width=True):
            _render_job_outcome(scheduler.run_fetch_job())

    if st.button("Reset timer state (mark as never run)"):
        scheduler.reset_state()
        st.success("Timer state reset.")
        st.rerun()

    # ─── Results of the last run ───
    if state.get("results"):
        st.subheader("Last Run Results")
        st.dataframe(pd.DataFrame(state["results"]),
                     use_container_width=True, hide_index=True)
        if state.get("last_run"):
            st.caption(f"Last run: {state['last_run']}")

    st.divider()
    st.markdown("""
**Run the background daemon** so that fetching continues while the app is closed:

```bash
python run_scheduler.py                 # check every 60 seconds
python run_scheduler.py --poll 30       # check every 30 seconds
```

Alternatively, schedule `python run_scheduler.py --once` with Windows Task
Scheduler or cron.
""")