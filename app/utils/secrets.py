"""
secrets.py — Centralised secret resolution.

Resolution order (highest priority first):

    1. Environment variables — OS environment or a local ``.env`` file
    2. Streamlit Secrets (``.streamlit/secrets.toml``)
    3. An explicitly supplied fallback value

No credential is ever hardcoded in this repository: ``.env`` is git-ignored and
``.env.example`` documents every supported variable. This module deliberately
has no third-party dependencies so it stays import-safe everywhere.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

DEFAULT_GSHEET_CREDENTIALS = "creds/service_account.json"

_env_loaded = False


# ─────────────────────── Environment file loading ───────────────────────
def load_env_file(path=None, override=False):
    """Load ``KEY=VALUE`` pairs from a .env file into ``os.environ``.

    A small dependency-free parser supporting comments, blank lines, an
    optional ``export`` prefix, and single/double quoted values. Values already
    present in the environment win unless ``override`` is set.

    Returns:
        bool: True if a .env file was found and parsed.
    """
    global _env_loaded
    _env_loaded = True

    env_path = Path(path) if path else ENV_FILE
    if not env_path.exists():
        return False

    try:
        raw = env_path.read_text(encoding="utf-8")
    except OSError:
        return False

    for line in raw.splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry.startswith("export "):
            entry = entry[len("export "):].strip()
        if "=" not in entry:
            continue

        key, _, value = entry.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and (override or key not in os.environ):
            os.environ[key] = value

    return True


def env_file_loaded():
    """Whether :func:`load_env_file` has already run in this process."""
    return _env_loaded


# ─────────────────────── Secret resolution ───────────────────────
def _from_streamlit(*keys):
    """Read a dotted path from Streamlit Secrets, or None when unavailable."""
    if not keys:
        return None
    try:
        import streamlit as st

        node = st.secrets
        for key in keys:
            node = node[key]
        return node
    except Exception:
        return None


def get_secret(env_names, secrets_path=None, default=""):
    """Resolve a single secret value.

    Args:
        env_names: environment variable name, or a sequence of names to try.
        secrets_path: dotted Streamlit Secrets path, e.g. ``("ringba", "api_token")``.
        default: returned when nothing is configured.
    """
    load_env_file()

    names = [env_names] if isinstance(env_names, str) else list(env_names or [])
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()

    if secrets_path:
        value = _from_streamlit(*secrets_path)
        if value and str(value).strip():
            return str(value).strip()

    return default


def get_ringba_token(explicit=""):
    """Ringba API token.

    A token explicitly stored for a source takes precedence; otherwise the
    value is resolved from the environment or Streamlit Secrets.
    """
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return get_secret(
        ("RINGBA_API_TOKEN", "RINGBA_TOKEN"),
        secrets_path=("ringba", "api_token"),
    )


def get_ringba_account_id(explicit=""):
    """Ringba account identifier."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return get_secret(
        ("RINGBA_ACCOUNT_ID", "RINGBA_ACCOUNT"),
        secrets_path=("ringba", "account_id"),
    )


def get_api_token(explicit=""):
    """Bearer token / API key for a generic API source."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return get_secret(("API_TOKEN", "API_KEY"), secrets_path=("api", "token"))


def get_google_credentials_file(explicit=""):
    """Path to the Google service-account JSON key used by Sheets sources."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return get_secret(
        ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_SERVICE_ACCOUNT_FILE"),
        secrets_path=("google", "credentials_file"),
        default=DEFAULT_GSHEET_CREDENTIALS,
    )


def get_cookie_key(default=""):
    """Session cookie signing key.

    Override the value stored in users.yaml / Streamlit Secrets by setting
    ``CCT_COOKIE_KEY``; recommended for production deployments.
    """
    return get_secret(
        ("CCT_COOKIE_KEY", "STREAMLIT_COOKIE_KEY"),
        secrets_path=("users", "cookie", "key"),
        default=default,
    )


# ─────────────────────── Display helpers ───────────────────────
def mask_secret(value, keep_last=4):
    """Mask a secret for safe display, e.g. ``••••••1234``."""
    text = str(value or "").strip()
    if not text:
        return "(not set)"
    if len(text) <= keep_last:
        return "*" * len(text)
    return "*" * max(6, len(text) - keep_last) + text[-keep_last:]


def is_configured(value):
    """True when a secret value is present."""
    return bool(str(value or "").strip())