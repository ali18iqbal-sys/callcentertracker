"""
sources_manager.py — Data source registry.

Sources are stored in ``data/sources.yaml``. That file may contain credentials,
so it is git-ignored; values that are not stored on disk are resolved from the
environment or Streamlit Secrets at fetch time.
"""

from pathlib import Path
import yaml

import streamlit as st

from app.utils.secrets import get_ringba_account_id, get_ringba_token

SOURCES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "sources.yaml"

_KINDS = ("google_sheets", "apis", "ringba")


@st.cache_data(show_spinner=False)
def load_sources():
    """Load configured data sources (cached; invalidated on write)."""
    if not SOURCES_FILE.exists():
        return {kind: [] for kind in _KINDS}

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for kind in _KINDS:
        data.setdefault(kind, [])
    return data


def save_sources(sources):
    """Persist sources to disk and refresh the in-memory cache."""
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        yaml.dump(sources, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    load_sources.clear()


def resolve_ringba_credentials(source):
    """Resolve the account ID and API token for a Ringba source.

    Args:
        source: a Ringba entry returned by :func:`load_sources`.

    Returns:
        tuple[str, str]: ``(account_id, api_token)``

    A value stored with the source takes precedence; otherwise it is read from
    the environment (``RINGBA_ACCOUNT_ID`` / ``RINGBA_API_TOKEN``) or from
    Streamlit Secrets. This allows tokens to stay out of ``sources.yaml``.
    """
    return (
        get_ringba_account_id(source.get("account_id")),
        get_ringba_token(source.get("api_token")),
    )


def add_gsheet(name, url, source_type, sheet_name, credential_file):
    """Register a Google Sheets source."""
    sources = load_sources()
    sources["google_sheets"].append({
        "name": name, "url": url, "type": source_type,
        "sheet_name": sheet_name or "",
        "credential_file": credential_file, "enabled": True,
    })
    save_sources(sources)


def add_api(name, url, source_type, auth_type, auth_value, json_path):
    """Register a generic API source."""
    sources = load_sources()
    sources["apis"].append({
        "name": name, "url": url, "type": source_type,
        "auth_type": auth_type, "auth_value": auth_value or "",
        "json_path": json_path or "", "enabled": True,
    })
    save_sources(sources)


def delete_source(source_kind, index):
    """Delete a source by position. Returns True when something was removed."""
    sources = load_sources()
    if 0 <= index < len(sources[source_kind]):
        sources[source_kind].pop(index)
        save_sources(sources)
        return True
    return False


# ─────────────── Ringba sources ───────────────
def add_ringba(name, account_id, api_token, data_type="cc",
               report_days=1, enabled=True):
    """Register a Ringba source used for automatic call-log fetching."""
    sources = load_sources()
    sources["ringba"].append({
        "name": name,
        "account_id": account_id or "",
        "api_token": api_token or "",
        "data_type": data_type if data_type in ("client", "cc") else "cc",
        "report_days": int(report_days) if report_days is not None else 1,
        "enabled": bool(enabled),
    })
    save_sources(sources)


def toggle_source(source_kind, index):
    """Enable or disable a source. Returns the new state, or None if not found."""
    sources = load_sources()
    if 0 <= index < len(sources.get(source_kind, [])):
        src = sources[source_kind][index]
        src["enabled"] = not src.get("enabled", True)
        save_sources(sources)
        return src["enabled"]
    return None