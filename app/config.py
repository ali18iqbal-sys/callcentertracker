"""
config.py — Configuration loader
Yeh file config.yaml ko read karke Python dictionary mein badalti hai.
"""

from pathlib import Path
import yaml

# Project ka root folder (jahan config.yaml hai)
ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.yaml"


def load_config():
    """config.yaml file load karo"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file nahi mili: {CONFIG_FILE}")
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    return cfg


# Ek baar load karo, sab jagah use karo
CONFIG = load_config()


def get(path, default=None):
    """
    Config se value nikaalo dot notation se.
    Example: get("app.name")  →  "CallCenterTracker"
    """
    keys = path.split(".")
    value = CONFIG
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def get_abs_path(folder_key):
    """Relative path ko absolute banao"""
    rel = CONFIG["paths"].get(folder_key)
    if not rel:
        return None
    abs_path = ROOT_DIR / rel
    abs_path.mkdir(parents=True, exist_ok=True)
    return abs_path