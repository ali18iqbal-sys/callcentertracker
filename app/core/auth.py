"""
auth.py — Login / Authentication helpers + User CRUD
"""

from pathlib import Path
import yaml
import streamlit as st
import streamlit_authenticator as stauth


USERS_FILE = Path(__file__).parent.parent.parent / "users.yaml"


def load_users_config():
    """
    Users config load karo.
    Pehle local users.yaml try karo, agar nahi mili toh Streamlit Secrets se.
    """
    # ─── Try 1: Local file (development) ───
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    # ─── Try 2: Streamlit Secrets (production) ───
    try:
        import streamlit as st
        if "users" in st.secrets:
            return dict(st.secrets["users"])
    except Exception:
        pass
    
    raise FileNotFoundError(
        "Users config nahi mili. Local 'users.yaml' ya Streamlit Secrets mein 'users' key daalein."
    )


def save_users_config(config):
    """
    Users config save karo.
    ⚠️ Streamlit Cloud par yeh save nahi hoga — sirf local development ke liye.
    Production mein user changes manually Streamlit Secrets mein karein.
    """
    try:
        # Local file mein save karo (development)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        # Streamlit Cloud check
        import streamlit as st
        if hasattr(st, "runtime") and hasattr(st.runtime, "exists"):
            try:
                # Agar cloud par chal rahe hain
                if st.runtime.exists():
                    st.warning(
                        "⚠️ User changes saved locally, lekin Streamlit Cloud par reflect nahi honge. "
                        "Cloud ke liye Streamlit Secrets update karein."
                    )
            except Exception:
                pass
    except Exception as e:
        # Cloud par file write fail ho sakti hai
        raise IOError(
            f"User config save nahi ho saka. "
            f"Streamlit Cloud par direct Secrets edit karein. Error: {e}"
        )


def create_authenticator():
    """
    Authenticator object banao.
    ⚠️ Yeh function har run mein SIRF EK BAAR call hona chahiye.
    """
    config = load_users_config()
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return authenticator


def get_current_user():
    """Current logged-in user ka info do"""
    if not st.session_state.get("authentication_status"):
        return None
    
    username = st.session_state.get("username")
    if not username:
        return None
    
    config = load_users_config()
    user_info = config["credentials"]["usernames"].get(username, {})
    
    return {
        "username": username,
        "name": st.session_state.get("name", username),
        "email": user_info.get("email", ""),
        "role": user_info.get("role", "user"),
    }


def is_master():
    """Kya current user master hai?"""
    user = get_current_user()
    return user is not None and user.get("role") == "master"


def hash_password(password):
    """Password ko hash karo"""
    return stauth.Hasher.hash(password)


# ─────────────── User CRUD ───────────────
def list_users():
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
    if not username or not password:
        return False, "Username aur password zaroori hain"
    
    config = load_users_config()
    
    if username in config["credentials"]["usernames"]:
        return False, f"Username '{username}' pehle se mojood hai"
    
    config["credentials"]["usernames"][username] = {
        "email": email or f"{username}@callcenter.local",
        "name": name or username,
        "password": hash_password(password),
        "role": role,
        "disabled": False,
    }
    
    save_users_config(config)
    return True, f"User '{username}' add ho gaya"


def update_user(username, name=None, email=None, role=None):
    config = load_users_config()
    
    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' nahi mila"
    
    user = config["credentials"]["usernames"][username]
    if name is not None:
        user["name"] = name
    if email is not None:
        user["email"] = email
    if role is not None:
        user["role"] = role
    
    save_users_config(config)
    return True, f"User '{username}' update ho gaya"


def change_password(username, new_password):
    config = load_users_config()
    
    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' nahi mila"
    
    config["credentials"]["usernames"][username]["password"] = hash_password(new_password)
    save_users_config(config)
    return True, f"Password '{username}' ka change ho gaya"


def toggle_user_disabled(username):
    config = load_users_config()
    
    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' nahi mila"
    
    user = config["credentials"]["usernames"][username]
    current = user.get("disabled", False)
    user["disabled"] = not current
    save_users_config(config)
    
    status = "disabled" if not current else "enabled"
    return True, f"User '{username}' {status} ho gaya"


def delete_user(username):
    config = load_users_config()
    
    if username not in config["credentials"]["usernames"]:
        return False, f"User '{username}' nahi mila"
    
    if username == "admin":
        return False, "Admin user ko delete nahi kar sakte"
    
    del config["credentials"]["usernames"][username]
    save_users_config(config)
    return True, f"User '{username}' delete ho gaya"