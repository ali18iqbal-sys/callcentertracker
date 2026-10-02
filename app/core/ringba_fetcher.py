"""
ringba_fetcher.py — Call log fetcher for the Ringba API.

Ringba API v2:
    Base URL : https://api.ringba.com/v2
    Endpoint : POST /{accountId}/calllogs
    Auth     : Authorization: Token <api_token>
    Body     : {"reportStart": ISO8601, "reportEnd": ISO8601,
                "size": N, "offset": M}
    Response : records are read from "report.records[]" (current) or
               "callLog.data[]" (legacy) — both envelopes are supported.

This module only handles the network layer and normalisation. Scheduling is
implemented in app/core/scheduler.py.

Credentials are resolved through app.utils.secrets (environment variables or
Streamlit Secrets) whenever an explicit token is not supplied.
"""

from datetime import date, datetime, timezone

import pandas as pd
import requests

from app.utils.secrets import get_ringba_account_id, get_ringba_token


RINGBA_BASE_URL = "https://api.ringba.com/v2"
DEFAULT_PAGE_SIZE = 100
MAX_RECORDS_SAFETY = 200_000
DEFAULT_TIMEOUT = 60


class RingbaError(Exception):
    """Raised for Ringba fetch, authentication, or parsing failures."""


# ─────────────── Ringba field → standard column mapping ───────────────
# Candidate field names per standard column; the first match wins.
RINGBA_FIELD_CANDIDATES = {
    "phone": [
        "inboundPhoneNumber", "callerId", "phoneNumber",
        "callerNumber", "from", "ani", "inboundNumber",
    ],
    "date": [
        "callDt", "callDate", "startDate", "lastUpdateDt",
        "date", "timestamp", "createdOn",
    ],
    "duration_seconds": [
        "callLengthInSeconds", "connectedCallLengthInSeconds",
        "callLength", "duration", "durationSeconds",
    ],
    "team": [
        "campaignName", "campaign", "buyerName", "tag_Campaign",
    ],
    "dialer": [
        "targetName", "publisherName", "target", "publisher",
        "affiliateName", "agentName", "tag_Target", "tag_Publisher",
    ],
    "call_id": [
        "inboundCallId", "callId", "id", "ringbaCallId",
    ],
    "status": [
        "callStatus", "status", "completed", "state",
    ],
}


# ─────────────── Internal helpers ───────────────
def _iso(value):
    """Convert a date/datetime/str into a Ringba-compatible ISO-8601 UTC string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return datetime(
            value.year, value.month, value.day, tzinfo=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


def _auth_headers(api_token):
    if not api_token:
        raise RingbaError("A Ringba API token is required.")
    return {
        "Authorization": f"Token {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _raise_for_status(resp):
    """Convert an HTTP error response into a descriptive RingbaError."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = getattr(resp, "status_code", "?")
        body = ""
        try:
            body = (resp.text or "")[:300]
        except Exception:
            pass
        if status == 401:
            raise RingbaError(
                f"Ringba authentication failed (401). Verify the API token. {body}"
            ) from exc
        if status == 403:
            raise RingbaError(
                f"Ringba access denied (403). Verify the account and token permissions. {body}"
            ) from exc
        if status == 404:
            raise RingbaError(
                f"Ringba endpoint not found (404). Verify the account ID and base URL. {body}"
            ) from exc
        raise RingbaError(f"Ringba HTTP error {status}: {body}") from exc


def _extract_records(payload):
    """Extract the record list from the supported Ringba response shapes.

    Supported envelopes:
        - list (direct)
        - {"records|data|items|results|callLogs": [...]}
        - {"report": {"records|data|items": [...]}}
        - {"callLog": {"data": [...]}}
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise RingbaError("Unexpected Ringba response structure.")

    for key in ("records", "data", "items", "results", "callLogs"):
        val = payload.get(key)
        if isinstance(val, list):
            return val

    report = payload.get("report")
    if isinstance(report, dict):
        for key in ("records", "data", "items"):
            val = report.get(key)
            if isinstance(val, list):
                return val

    call_log = payload.get("callLog") or payload.get("calllog")
    if isinstance(call_log, dict):
        val = call_log.get("data")
        if isinstance(val, list):
            return val

    return []


def _extract_total(payload):
    """Extract the total record count (used to stop pagination early)."""
    if not isinstance(payload, dict):
        return None
    containers = [payload, payload.get("report"), payload.get("callLog")]
    for container in containers:
        if isinstance(container, dict):
            for key in ("recordCount", "totalCount", "total", "count", "totalRecords"):
                val = container.get(key)
                if isinstance(val, int):
                    return val
    return None


# ─────────────── Public API ───────────────
def fetch_ringba_calls(
    account_id,
    api_token,
    report_start,
    report_end,
    base_url=RINGBA_BASE_URL,
    page_size=DEFAULT_PAGE_SIZE,
    offset=0,
    max_records=MAX_RECORDS_SAFETY,
    filters=None,
    timeout=DEFAULT_TIMEOUT,
    session=None,
):
    """
    Fetch Ringba call logs (paginated).

    Args:
        account_id: Ringba account ID. Falls back to ``RINGBA_ACCOUNT_ID`` or
            Streamlit Secrets when not supplied.
        api_token: Ringba API token (Authorization: Token ...). Falls back to
            ``RINGBA_API_TOKEN`` or Streamlit Secrets when not supplied.
        report_start / report_end: date | datetime | ISO string
        base_url: default https://api.ringba.com/v2
        page_size: per-page size (Ringba "size")
        offset: start offset
        max_records: safety cap
        filters: optional Ringba filters list
        timeout: HTTP timeout (seconds)
        session: requests.Session or compatible object (injectable for tests)

    Returns:
        pd.DataFrame (raw Ringba records)
    """
    account_id = get_ringba_account_id(account_id)
    api_token = get_ringba_token(api_token)

    if not account_id:
        raise RingbaError("A Ringba account ID is required.")

    url = f"{str(base_url).rstrip('/')}/{account_id}/calllogs"
    headers = _auth_headers(api_token)
    sess = session or requests

    page_size = max(1, int(page_size))
    current = int(offset or 0)
    all_records = []
    pages = 0
    total = None

    while True:
        body = {
            "reportStart": _iso(report_start),
            "reportEnd": _iso(report_end),
            "size": page_size,
            "offset": current,
        }
        if filters:
            body["filters"] = filters

        resp = sess.post(url, headers=headers, json=body, timeout=timeout)
        _raise_for_status(resp)

        try:
            payload = resp.json()
        except Exception as exc:
            raise RingbaError(f"Ringba did not return valid JSON: {exc}") from exc

        records = _extract_records(payload)
        if total is None:
            total = _extract_total(payload)

        if not records:
            break

        all_records.extend(records)
        pages += 1

        if len(records) < page_size:
            break
        if total is not None and len(all_records) >= total:
            break
        if len(all_records) >= max_records:
            break

        current += page_size

    df = pd.DataFrame(all_records)
    df.attrs["ringba_pages"] = pages
    df.attrs["ringba_total"] = total
    return df


def _first_present(columns, candidates):
    """Return the first matching column from the candidates (case-insensitive)."""
    for cand in candidates:
        if cand in columns:
            return cand
    lower = {str(c).lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def normalize_ringba(df, seconds_to_minutes=True):
    """Normalise a raw Ringba DataFrame into the tracker's standard columns.

    Output: phone, date, minutes, team, dialer, calls
    (plus ringba_call_id / status when available).
    """
    standard_cols = ["phone", "date", "minutes", "team", "dialer", "calls"]
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=standard_cols)

    cols = list(df.columns)
    out = pd.DataFrame(index=df.index)

    phone_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["phone"])
    if phone_col:
        out["phone"] = df[phone_col]

    date_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["date"])
    if date_col:
        out["date"] = df[date_col]

    dur_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["duration_seconds"])
    if dur_col:
        secs = pd.to_numeric(df[dur_col], errors="coerce")
        out["minutes"] = (secs / 60.0).round(2) if seconds_to_minutes else secs

    team_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["team"])
    if team_col:
        out["team"] = df[team_col]

    dialer_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["dialer"])
    if dialer_col:
        out["dialer"] = df[dialer_col]

    id_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["call_id"])
    if id_col:
        out["ringba_call_id"] = df[id_col]

    status_col = _first_present(cols, RINGBA_FIELD_CANDIDATES["status"])
    if status_col:
        out["status"] = df[status_col]

    out["calls"] = 1
    out["_source"] = "Ringba"

    return out.reset_index(drop=True)


def fetch_ringba_as_standard(account_id, api_token, report_start, report_end, **kwargs):
    """Fetch and normalise in a single call (used by auto-fetch jobs)."""
    raw = fetch_ringba_calls(account_id, api_token, report_start, report_end, **kwargs)
    return normalize_ringba(raw)
