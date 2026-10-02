"""
test_ui_smoke.py — Streamlit app boot + page render smoke tests (AppTest).

Also covers the presentation theme and the secret resolution helpers.

Run from the project root:

    python tests/test_ui_smoke.py

With pytest:

    pytest tests/test_ui_smoke.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from app.utils import secrets, styles

APP = str(ROOT / "app.py")
NAV_PAGES = [
    "Upload", "Data Sources", "Results", "Performance",
    "Missing", "Targets", "Reports", "Master Panel",
]


def _logged_in_app(page=None):
    """Run the app in a logged-in state, optionally navigating to one page."""
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["authentication_status"] = True
    at.session_state["username"] = "admin"
    at.session_state["name"] = "Admin"
    at.run()
    if page is not None:
        at.radio(key="main_nav_radio").set_value(page)
        at.run()
    return at


# ═══════════════════════════════════════════════════════════
#  TESTS
# ═══════════════════════════════════════════════════════════
def test_app_boots_without_exception():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception, at.exception


def test_all_pages_render_without_exception():
    for page in NAV_PAGES:
        at = _logged_in_app(page)
        assert not at.exception, f"{page} page raised: {at.exception}"


def test_data_sources_has_ringba_and_schedule_tabs():
    at = _logged_in_app("Data Sources")
    assert not at.exception, at.exception

    labels = [t.label for t in at.tabs]
    assert "Ringba" in labels, labels
    assert "Schedule" in labels, labels

    subheaders = [s.value for s in at.subheader]
    assert "Ringba Sources" in subheaders, subheaders
    assert "Auto-Fetch Timer" in subheaders, subheaders


def test_schedule_tab_has_controls():
    at = _logged_in_app("Data Sources")
    assert not at.exception, at.exception

    checkbox_labels = [c.label for c in at.checkbox]
    assert "Enable auto-fetch" in checkbox_labels, checkbox_labels

    input_labels = [t.label for t in at.text_input]
    assert "Execution Times (24-hour clock, comma separated)" in input_labels, input_labels


def test_upload_page_renders_merge_section():
    at = _logged_in_app("Upload")
    assert not at.exception, at.exception
    subheaders = [s.value for s in at.subheader]
    # Client + CC upload columns
    assert any("Client Data" in s for s in subheaders), subheaders
    assert any("Call Center Data" in s for s in subheaders), subheaders


# ═══════════════════════════════════════════════════════════
#  THEME + SECURITY REGRESSIONS
# ═══════════════════════════════════════════════════════════
LEGACY_DARK_VALUES = (
    "#6366F1",   # previous indigo primary
    "#8B5CF6",   # previous violet
    "#06B6D4",   # previous cyan accent
    "#0B1120",   # previous dark sidebar
    "131A34",
    "1E1B4B",
)


def test_theme_uses_light_corporate_palette():
    """The theme must stay on the light corporate blue palette."""
    assert styles.PRIMARY == "#2563EB"
    assert styles.BACKGROUND == "#F8FAFC"
    assert styles.SURFACE == "#FFFFFF"

    css = styles._CSS
    for legacy in LEGACY_DARK_VALUES:
        assert legacy.lower() not in css.lower(), f"legacy theme value present: {legacy}"

    # No remote font downloads — first paint must stay fast
    assert "@import url(" not in css


def test_streamlit_config_matches_theme():
    """.streamlit/config.toml must use the same light palette."""
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#2563EB"' in config
    assert 'backgroundColor = "#F8FAFC"' in config
    assert 'secondaryBackgroundColor = "#FFFFFF"' in config
    assert 'base = "light"' in config


def test_security_files_exist_and_ignore_secrets():
    """The standard safety files must exist and cover the sensitive paths."""
    assert (ROOT / "requirements.txt").exists()
    assert (ROOT / ".gitignore").exists()
    assert (ROOT / ".env.example").exists()

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", "users.yaml", "data/sources.yaml", ".streamlit/secrets.toml"):
        assert pattern in ignore, f"missing gitignore entry: {pattern}"
    assert "!.env.example" in ignore


def test_secrets_resolve_from_environment():
    """Secrets must resolve from the environment, with explicit values winning."""
    previous = os.environ.get("RINGBA_API_TOKEN")
    try:
        os.environ["RINGBA_API_TOKEN"] = "env-token-1234"
        assert secrets.get_ringba_token() == "env-token-1234"
        assert secrets.get_ringba_token("explicit-token") == "explicit-token"

        assert secrets.mask_secret("env-token-1234").endswith("1234")
        assert "env-token" not in secrets.mask_secret("env-token-1234")
        assert secrets.mask_secret("") == "(not set)"
    finally:
        if previous is None:
            os.environ.pop("RINGBA_API_TOKEN", None)
        else:
            os.environ["RINGBA_API_TOKEN"] = previous


# ═══════════════════════════════════════════════════════════
#  RUNNER
# ═══════════════════════════════════════════════════════════
def _all_tests():
    return [v for k, v in sorted(globals().items())
            if k.startswith("test_") and callable(v)]


def main():
    tests = _all_tests()
    passed = 0
    failed = []

    print("=" * 60)
    print("  CallCenterTracker — UI Smoke Tests")
    print("=" * 60)

    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {t.__name__}: {exc}")
            failed.append(t.__name__)

    print("-" * 60)
    print(f"  {passed}/{len(tests)} tests passed")
    if failed:
        print("  Failed: " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
