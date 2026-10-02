"""
auth.py — Authentication helpers and user management.

User records are loaded from a local ``users.yaml`` (development) or from
Streamlit Secrets (production). Passwords are only ever stored as bcrypt
hashes, and the cookie signing key may be overridden with the
``CCT_COOKIE_KEY`` environment variable.
"""

from pathlib import Path
import yaml
import streamlit as st
import streamlit_authenticator as stauth

from app.utils.secrets import get_cookie_key


USERS_FILE = Path(__file__).resolve().parent.parent.parent / "users.yaml"

MISSING_USERS_MESSAGE = (
    "Authentication configuration was not found. Provide a users.yaml file in "
    "the project root for local development, or a 'users' section in Streamlit "
    "Secrets for production deployments."
)


def _plain(value):
    """Recursively convert Streamlit secret objects into plain Python values."""
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@st.cache_data(show_spinner=False)
def load_users_config():
    """Load the users configuration.

    Results are cached to avoid re-reading the file on every rerun; the cache is
    invalidated automatically whenever the configuration is saved.
    """
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return _plain(yaml.safe_load(f) or {})

    try:
        if "users" in st.secrets:
            return _plain(dict(st.secrets["users"]))
    except Exception:
        pass

    raise FileNotFoundError(MISSING_USERS_MESSAGE)


def save_users_config(config):
    """Persist the users configuration to the local users.yaml file.

    Warning:
        Streamlit Cloud deployments are read-only. On such deployments, update
        user records through Streamlit Secrets instead.
    """
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except OSError as exc:
        raise IOError(
            "The user configuration could not be saved. On Streamlit Cloud, "
            f"update the Secrets file directly. Details: {exc}"
        ) from exc

    load_users_config.clear()


def create_authenticator():
    """Build the authentication widget handler.

    A fresh handler is created on every rerun on purpose: it guarantees that
    disabled accounts and password changes take effect immediately. The file
    read behind it is cached, so this stays inexpensive.
    """
    config = load_users_config()
    cookie = config.get("cookie", {}) or {}
    return stauth.Authenticate(
        config["credentials"],
        cookie.get("name", "cct_cookie"),
        get_cookie_key(cookie.get("key", "")),
        int(cookie.get("expiry_days", 1)),
    )


def get_current_user():
    """Return the currently authenticated user's profile, or None."""
    if not st.session_state.get("authentication_status"):
        return None

    username = st.session_state.get("username")
    if not username:
        return None

    config = load_users_config()
    user_info = config.get("credentials", {}).get("usernames", {}).get(username, {})

    return {
        "username": username,
        "name": st.session_state.get("name", username),
        "email": user_info.get("email", ""),
        "role": user_info.get("role", "user"),
    }


def is_master():
    """True when the current user holds the master (administrator) role."""
    user = get_current_user()
    return user is not None and user.get("role") == "master"


def hash_password(password):
    """Hash a plaintext password with bcrypt."""
    return stauth.Hasher.hash(password)


# ─────────────── User CRUD ───────────────
def list_users():
    """Return every configured user as a list of dictionaries."""
    config = load_users_config()
    users = []
    for username, info in config["credentials"]["usernames"].items():
        users.append({
            "username": username,
            "name": info.get("name", ""),
            "email": info.get("email", ""),
            "role": info.get("role", "user"),
            "disabled": info.get("disabled", False),
        })
    return users


def add_user(username, name, email, password, role="user"):
    """Create a new user account.

    Returns:
        tuple[bool, str]: success flag and a human-readable status message.
    """
    if not username or not password:
        return False, "Username and password are required."

    config = load_users_config()

    if username in config["credentials"]["usernames"]:
        return False, f"Username '{username}' already exists."

    config["credentials"]["usernames"][username] = {
        "email": email or f"{username}@callcenter.local",
        "name": name or username,
        "password": hash_password(password),
        "role": role,
        "disabled": False,
    }

    save_users_config(config)
    return True, f"User '{username}' was created successfully."


def update_user(username, name=None, email=None, role=None):
    """Update a user's profile fields. Returns (success, message)."""
    config = load_users_config()

    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' was not found."

    user = config["credentials"]["usernames"][username]
    if name is not None:
        user["name"] = name
    if email is not None:
        user["email"] = email
    if role is not None:
        user["role"] = role

    save_users_config(config)
    return True, f"User '{username}' was updated successfully."


def change_password(username, new_password):
    """Set a new password for a user. Returns (success, message)."""
    config = load_users_config()

    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' was not found."

    config["credentials"]["usernames"][username]["password"] = hash_password(new_password)
    save_users_config(config)
    return True, f"The password for '{username}' was updated successfully."


def toggle_user_disabled(username):
    """Enable or disable a user account. Returns (success, message)."""
    config = load_users_config()

    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' was not found."

    user = config["credentials"]["usernames"][username]
    current = user.get("disabled", False)
    user["disabled"] = not current
    save_users_config(config)

    status = "disabled" if not current else "enabled"
    return True, f"User '{username}' was {status} successfully."


def delete_user(username):
    """Delete a user account. Returns (success, message)."""
    config = load_users_config()

    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' was not found."

    if username == "admin":
        return False, "The admin account cannot be deleted."

    del config["credentials"]["usernames"][username]
    save_users_config(config)
    return True, f"User '{username}' was deleted successfully."