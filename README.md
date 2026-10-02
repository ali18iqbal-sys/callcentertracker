# CallCenterTracker

Sales-conversion tracking for a call center. It reconciles two datasets — a
**client's sales file** (phone → sale, usually with price/amount) and the
**call center's dialer log** (phone → every call, with team/dialer/minutes/date)
— and reports which calls actually converted.

Every phone number is sorted into one of three buckets:

- **Sold** — present in both: the call center called it *and* it converted.
- **No-Sale** — the call center called it, but no sale appears client-side.
- **Orphan** — a client sale with no matching call in the call-center log.

From that it builds overall / team / dialer conversion dashboards, compares
against call targets, and offers a custom report builder.

## Stack

Python + Streamlit, pandas, openpyxl, gspread/google-auth, requests, PyYAML,
and streamlit-authenticator. Config lives in `config.yaml`; persistence is YAML
+ files under `data/` (no database).

## Run

```bash
pip install -r requirements.txt
copy .env.example .env      # optional: configure credentials
streamlit run app.py
```

The dev container (`.devcontainer/`) starts Streamlit on port 8501 automatically.

Login users live in `users.yaml` (development) or Streamlit Secrets (production).

## Configuration & secrets

No credential is hardcoded. `app/utils/secrets.py` resolves every secret in this
order:

1. Environment variables — the OS environment or a local `.env` file
2. Streamlit Secrets (`.streamlit/secrets.toml`)
3. A value stored against the data source itself

| Variable | Purpose |
| --- | --- |
| `RINGBA_ACCOUNT_ID` | Ringba account identifier |
| `RINGBA_API_TOKEN` | Ringba API token |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service-account JSON key for Google Sheets |
| `API_TOKEN` | Fallback token for generic API sources |
| `CCT_COOKIE_KEY` | Session cookie signing key (recommended in production) |

`.env` is git-ignored, and `.env.example` documents every supported value.
`users.yaml`, `data/sources.yaml` and `data/fetched/` are also git-ignored
because they contain password hashes, cookie keys or API tokens.

## Performance

- `app/utils/caching.py` centralises all `@st.cache_data` usage: uploaded file
  parsing, the client ↔ call center reconciliation, Excel exports and dashboard
  analytics are computed once and reused across reruns.
- `app/utils/session.py` memoises the concatenated client/call center frames,
  so switching pages never re-concatenates files.
- The UI uses a native system font stack (no external font downloads) and a
  single compact stylesheet, keeping first paint fast.

## Theme

A single light corporate SaaS theme: `#F8FAFC` background, `#FFFFFF` cards with
soft subtle shadows, and `#2563EB` corporate blue accents. Widget colours live
in `.streamlit/config.toml`; component styling lives in `app/utils/styles.py`.

## Features

### 1. Excel multi-sheet merging

Any uploaded Excel workbook is read **sheet by sheet and merged into one
consolidated dataset**, on both the Client side and the Call Center side. Every
row is tagged with a `_source_sheet` column so you can trace provenance, and
empty/blank sheets are skipped automatically. Single-sheet files work unchanged.

The Upload page shows a **"Consolidated Sheet (Multi-Sheet Merge)"** section with
a one-click download of the merged Client and CC sheets as single-sheet Excel
files (`client_consolidated.xlsx`, `cc_consolidated.xlsx`).

Code: `app/core/reader.py` (`read_excel`, `list_excel_sheets`), helper
`app/utils/excel_io.py`.

### 2. Ringba API integration

Fetch call logs directly from Ringba (API v2).

- Base URL: `https://api.ringba.com/v2`
- Endpoint: `POST /{accountId}/calllogs`
- Auth: `Authorization: Token <api_token>`
- Body: `{reportStart, reportEnd, size, offset}` (dates computed as
  `today - report_days` → `today`)
- Pagination handled automatically; both response envelopes are supported
  (`report.records[]` and `callLog.data[]`)

Add a source under **Data Sources → Ringba** (name, account ID, API token,
data type, report window), then "Fetch Now". Ringba fields are normalized to the
tracker's standard columns (`phone`, `date`, `minutes`, `team`, `dialer`).

Code: `app/core/ringba_fetcher.py`.

### 3. Auto-fetch timer / scheduling

Configure when auto-fetch runs, either:

- **interval** — every N minutes, or
- **times** — at specific times each day (e.g. `09:00, 13:00, 18:00`)

Config lives in `data/schedule.yaml` and is editable from the UI in
**Data Sources → Schedule**. The tab shows Status / Last run / Next run, lets you
run due jobs, force a fetch, reset timer state, and limit the run to specific
sources.

**In-app**: click "Run due now" (or "Force fetch now").

**Background daemon** (runs even when the app is closed):

```bash
python run_scheduler.py                 # check every 60s
python run_scheduler.py --poll 30       # check every 30s
python run_scheduler.py --once          # single due-check then exit (cron / Task Scheduler)
python run_scheduler.py --force         # ignore schedule, fetch now
python run_scheduler.py --days 3        # Ringba report window in days
```

On each run it fetches all enabled sources (Google Sheets / APIs / Ringba),
consolidates them, optionally writes `data/fetched/cc_latest.xlsx` and
`data/fetched/client_latest.xlsx`, and records state in `data/last_fetch.json`.

Code: `app/core/scheduler.py`, `run_scheduler.py`,
`app/core/sources_manager.py`.

## Tests

```bash
python tests/test_features.py     # 25 unit + integration tests (no network needed)
python tests/test_ui_smoke.py     # 9 Streamlit AppTest render + theme/security tests
```

The Ringba tests inject a fake HTTP session, so no live token is required. The
UI tests boot the real app and render every page via Streamlit's `AppTest`;
they also assert that the light theme and the security defaults stay in place.

## Notes

- `data/` outputs and `data/last_fetch.json` are gitignored; `data/schedule.yaml`
  is tracked as configuration.
- `users.yaml`, `data/sources.yaml` and credential files are never committed.
  They have been removed from git tracking — if they were pushed to a shared
  remote before, rotate the cookie key and the affected account passwords.
- Ringba tokens can be kept entirely out of `data/sources.yaml` by setting
  `RINGBA_ACCOUNT_ID` and `RINGBA_API_TOKEN` in `.env` or Streamlit Secrets;
  the Ringba form token field may then be left blank.
