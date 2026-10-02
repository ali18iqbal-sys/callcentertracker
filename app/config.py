"""
config.py — Configuration loader.

Reads ``config.yaml`` (project root) and exposes it through dotted lookups.
"""

from pathlib import Path
import yaml

# Project root (the directory containing config.yaml)
ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.yaml"


def load_config():
    """Load and parse config.yaml."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


# Load once at import time and reuse everywhere.
CONFIG = load_config()


def get(path, default=None):
    """Read a configuration value using dot notation.

    Example: get("app.name") → "CallCenterTracker"
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
    """Resolve a configured relative path to an absolute, existing directory."""
    rel = CONFIG["paths"].get(folder_key)
    if not rel:
        return None
    abs_path = ROOT_DIR / rel
    abs_path.mkdir(parents=True, exist_ok=True)
    return abs_path