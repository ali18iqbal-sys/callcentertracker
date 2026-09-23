"""sources_manager.py - Auto sources manage"""

from pathlib import Path
import yaml


SOURCES_FILE = Path(__file__).parent.parent.parent / "data" / "sources.yaml"


def load_sources():
    if not SOURCES_FILE.exists():
        return {"google_sheets": [], "apis": []}
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("google_sheets", [])
    data.setdefault("apis", [])
    return data


def save_sources(sources):
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        yaml.dump(sources, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def add_gsheet(name, url, source_type, sheet_name, credential_file):
    sources = load_sources()
    sources["google_sheets"].append({
        "name": name, "url": url, "type": source_type,
        "sheet_name": sheet_name or "",
        "credential_file": credential_file, "enabled": True,
    })
    save_sources(sources)


def add_api(name, url, source_type, auth_type, auth_value, json_path):
    sources = load_sources()
    sources["apis"].append({
        "name": name, "url": url, "type": source_type,
        "auth_type": auth_type, "auth_value": auth_value or "",
        "json_path": json_path or "", "enabled": True,
    })
    save_sources(sources)


def delete_source(source_kind, index):
    sources = load_sources()
    if 0 <= index < len(sources[source_kind]):
        sources[source_kind].pop(index)
        save_sources(sources)
        return True
    return False
