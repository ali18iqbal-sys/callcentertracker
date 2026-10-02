"""
styles.py — Global UI theme for CallCenterTracker (clean, light corporate SaaS).

All visual styling for the application is controlled from this single module:

    inject_global_css()                 → called once per run from app.py
    page_header(title, subtitle, icon)  → page hero title + subtitle
    card(key=None)                      → white surface container
    badge(text, tone)                   → small inline status pill

Design language:
    Background      #F8FAFC  (airy, light)
    Surfaces        #FFFFFF  (crisp cards, soft subtle shadow)
    Accent          #2563EB  (professional corporate blue)
    Typography      native system font stack — no external font requests,
                    so first paint stays fast and offline-friendly.

This module contains only CSS and small HTML helpers; no application logic.
"""

from itertools import count

import streamlit as st


# ─────────────────────── Design tokens (single source of truth) ───────────────────────
PRIMARY = "#2563EB"        # corporate blue — primary actions, accents
PRIMARY_DARK = "#1D4ED8"   # hover / emphasis
PRIMARY_SOFT = "#EFF6FF"   # tinted surfaces
ACCENT = "#0EA5E9"         # secondary highlight
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"

BACKGROUND = "#F8FAFC"
SURFACE = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#0F172A"
MUTED = "#64748B"


_CSS = r"""
<style>
/* ═══════════════════════════════════════════════════════════════
   DESIGN TOKENS + TYPOGRAPHY
   System font stack only — no external font downloads, faster paint.
   ═══════════════════════════════════════════════════════════════ */
:root {
    --cct-primary: #2563EB;
    --cct-primary-dark: #1D4ED8;
    --cct-primary-soft: #EFF6FF;
    --cct-accent: #0EA5E9;
    --cct-success: #16A34A;
    --cct-warning: #D97706;
    --cct-danger: #DC2626;
    --cct-bg: #F8FAFC;
    --cct-surface: #FFFFFF;
    --cct-text: #0F172A;
    --cct-muted: #64748B;
    --cct-border: #E2E8F0;
    --cct-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
    --cct-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 14px rgba(15, 23, 42, 0.05);
    --cct-radius: 14px;
    --cct-radius-sm: 10px;
}

html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"],
button, input, textarea, select {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif !important;
}

/* ═══════════════════════════════════════════════════════════════
   APP SHELL — airy light background
   ═══════════════════════════════════════════════════════════════ */
.stApp, [data-testid="stAppViewContainer"] { background: var(--cct-bg); }
[data-testid="stHeader"] { background: transparent; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

[data-testid="stMainBlockContainer"], .block-container {
    padding-top: 2.2rem;
    padding-bottom: 3.5rem;
    max-width: 1440px;
}

/* ═══════════════════════════════════════════════════════════════
   TYPOGRAPHY — crisp solid headings (no gradient text)
   ═══════════════════════════════════════════════════════════════ */
h1, h2, h3, h4 { color: var(--cct-text) !important; letter-spacing: -0.015em; }
[data-testid="stMainBlockContainer"] h1 {
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.15rem;
}
[data-testid="stMainBlockContainer"] h2 { font-size: 1.3rem !important; font-weight: 650 !important; }
[data-testid="stMainBlockContainer"] h3 { font-size: 1.08rem !important; font-weight: 600 !important; }
[data-testid="stCaptionContainer"] p, small { color: var(--cct-muted) !important; }

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR — light surface, subtle divider, pill navigation
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: var(--cct-surface);
    border-right: 1px solid var(--cct-border);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.1rem; }
[data-testid="stSidebar"] [data-testid="stDivider"] { border-color: var(--cct-border) !important; }

/* Sidebar buttons (Logout) */
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: var(--cct-surface) !important;
    color: var(--cct-text) !important;
    border: 1px solid var(--cct-border) !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--cct-primary-soft) !important;
    border-color: var(--cct-primary) !important;
    color: var(--cct-primary-dark) !important;
}

/* Navigation radio → clean pill list */
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] { gap: 4px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 8px 12px !important;
    margin: 0 !important;
    border-radius: var(--cct-radius-sm);
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: var(--cct-primary-soft); }
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: var(--cct-muted) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: var(--cct-primary);
    border-color: var(--cct-primary);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}

/* ═══════════════════════════════════════════════════════════════
   BUTTONS — flat corporate blue, quiet secondary
   ═══════════════════════════════════════════════════════════════ */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: var(--cct-radius-sm) !important;
    font-weight: 600 !important;
    transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
    background: var(--cct-primary) !important;
    border: 1px solid var(--cct-primary) !important;
    color: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(37, 99, 235, 0.25) !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
    background: var(--cct-primary-dark) !important;
    border-color: var(--cct-primary-dark) !important;
}
.stButton > button[kind="secondary"],
.stFormSubmitButton > button[kind="secondary"],
.stDownloadButton > button {
    background: var(--cct-surface) !important;
    color: var(--cct-text) !important;
    border: 1px solid var(--cct-border) !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover,
.stFormSubmitButton > button[kind="secondary"]:hover,
.stDownloadButton > button:hover {
    background: var(--cct-primary-soft) !important;
    border-color: var(--cct-primary) !important;
    color: var(--cct-primary-dark) !important;
}

/* ═══════════════════════════════════════════════════════════════
   INPUTS — white, softly rounded, dashed upload zone
   ═══════════════════════════════════════════════════════════════ */
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="select"] > div,
[data-baseweb="textarea"] {
    border-radius: var(--cct-radius-sm) !important;
}
[data-testid="stFileUploader"] section {
    background: var(--cct-surface);
    border: 1px dashed var(--cct-border) !important;
    border-radius: var(--cct-radius-sm) !important;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--cct-primary) !important; }

/* ═══════════════════════════════════════════════════════════════
   CARDS — crisp white surface + soft subtle shadow
   (styles.card() injects a stable st-key-cct-card-* class)
   ═══════════════════════════════════════════════════════════════ */
[class*="st-key-cct-card-"] {
    background: var(--cct-surface) !important;
    border: 1px solid var(--cct-border) !important;
    border-radius: var(--cct-radius) !important;
    box-shadow: var(--cct-shadow) !important;
    padding: 1.15rem 1.35rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   METRICS — quiet white tiles
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: var(--cct-surface);
    border: 1px solid var(--cct-border);
    border-radius: var(--cct-radius-sm);
    padding: 0.85rem 1rem;
    box-shadow: var(--cct-shadow-sm);
}
[data-testid="stMetricValue"] { color: var(--cct-text) !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] p { color: var(--cct-muted) !important; font-weight: 600 !important; }

/* ═══════════════════════════════════════════════════════════════
   TABS — clean underline style with blue active state
   ═══════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid var(--cct-border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--cct-radius-sm) var(--cct-radius-sm) 0 0 !important;
    padding: 8px 14px !important;
    font-weight: 600 !important;
    color: var(--cct-muted) !important;
    transition: color 0.15s ease, background 0.15s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--cct-primary-dark) !important;
    background: var(--cct-primary-soft);
}
.stTabs [aria-selected="true"] {
    color: var(--cct-primary-dark) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: var(--cct-primary) !important;
    height: 2px;
}
.stTabs [data-baseweb="tab-border"] { background: transparent !important; }

/* ═══════════════════════════════════════════════════════════════
   EXPANDERS / ALERTS / FORMS
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: var(--cct-surface) !important;
    border: 1px solid var(--cct-border) !important;
    border-radius: var(--cct-radius-sm) !important;
    box-shadow: var(--cct-shadow-sm) !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-weight: 600 !important; }
[data-testid="stExpander"] summary:hover { color: var(--cct-primary-dark) !important; }

[data-testid="stAlert"] {
    border-radius: var(--cct-radius-sm) !important;
    border: 1px solid var(--cct-border) !important;
    box-shadow: var(--cct-shadow-sm);
}

[data-testid="stForm"] {
    background: var(--cct-surface) !important;
    border: 1px solid var(--cct-border) !important;
    border-radius: var(--cct-radius) !important;
    box-shadow: var(--cct-shadow) !important;
    padding: 1.2rem 1.3rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   PROGRESS / SPINNER / DIVIDER / DATAFRAME / SCROLLBAR
   ═══════════════════════════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: var(--cct-primary) !important;
    border-radius: 999px;
}
.stSpinner > div { border-top-color: var(--cct-primary) !important; }
hr, [data-testid="stDivider"] { border-color: var(--cct-border) !important; opacity: 1; }
[data-testid="stDataFrame"] {
    border: 1px solid var(--cct-border);
    border-radius: var(--cct-radius-sm);
}
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: #CBD5E1;
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}
::-webkit-scrollbar-thumb:hover { background: #94A3B8; background-clip: padding-box; }

/* ═══════════════════════════════════════════════════════════════
   CUSTOM HTML COMPONENTS
   (brand block, user card, pills, hero header, login hero)
   ═══════════════════════════════════════════════════════════════ */
.cct-brand { display: flex; align-items: center; gap: 11px; padding: 2px 2px 12px; }
.cct-brand-logo {
    width: 40px; height: 40px; border-radius: 12px; flex: 0 0 40px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    background: var(--cct-primary);
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.28);
}
.cct-brand-name { font-weight: 700; font-size: 1.02rem; color: var(--cct-text); line-height: 1.25; }
.cct-brand-sub { font-size: 0.74rem; color: var(--cct-muted); }

.cct-user {
    display: flex; align-items: center; gap: 10px;
    background: var(--cct-primary-soft);
    border: 1px solid #DBEAFE;
    border-radius: var(--cct-radius-sm);
    padding: 9px 11px; margin: 4px 0 6px;
}
.cct-avatar {
    width: 36px; height: 36px; border-radius: 50%; flex: 0 0 36px;
    display: flex; align-items: center; justify-content: center;
    color: #FFFFFF; font-weight: 700; font-size: 0.86rem;
    background: var(--cct-primary);
}
.cct-user-name { font-weight: 700; font-size: 0.9rem; color: var(--cct-text); line-height: 1.2; }
.cct-user-role { font-size: 0.72rem; color: var(--cct-muted); }

/* Status pills */
.cct-pill {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; line-height: 1.7;
}
.cct-pill-master { background: var(--cct-primary); color: #FFFFFF; }
.cct-pill-user { background: var(--cct-primary-soft); color: var(--cct-primary-dark); border: 1px solid #BFDBFE; }
.cct-pill-success { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
.cct-pill-warn { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
.cct-pill-danger { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }

/* Page hero header */
.cct-hero { margin-bottom: 1rem; }
.cct-hero-title {
    font-size: 1.9rem !important; font-weight: 700 !important;
    letter-spacing: -0.02em; line-height: 1.15; margin: 0;
    color: var(--cct-text) !important;
}
.cct-hero-sub { color: var(--cct-muted) !important; font-size: 0.95rem; font-weight: 500; margin: 0; }
.cct-hero-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 42px; height: 42px; border-radius: 12px; font-size: 21px;
    margin-right: 10px; vertical-align: middle;
    background: var(--cct-surface);
    border: 1px solid var(--cct-border);
    box-shadow: var(--cct-shadow-sm);
}

/* Login hero */
.cct-login-logo {
    width: 62px; height: 62px; border-radius: 16px; margin: 6px auto 10px auto;
    display: flex; align-items: center; justify-content: center; font-size: 30px;
    background: var(--cct-primary);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.28);
}
.cct-login-title {
    text-align: center; font-size: 1.7rem; font-weight: 700;
    color: var(--cct-text); letter-spacing: -0.02em; margin: 0.2rem 0 0.15rem;
}
.cct-login-sub { text-align: center; color: var(--cct-muted); font-size: 0.9rem; margin-bottom: 0.4rem; }
</style>
"""


# ─────────────────────── Per-run card key counter ───────────────────────
# Reset at the start of every script run so that container keys stay stable
# across reruns (keeps DOM identity consistent and avoids duplicate keys).
# The key is what gives each card a targetable `st-key-cct-card-*` CSS class.
_card_keys = count()


def inject_global_css():
    """Inject the global stylesheet. Call once per run from app.py."""
    global _card_keys
    _card_keys = count()
    st.markdown(_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  Reusable visual components
# ═══════════════════════════════════════════════════════════════
_PILL_TONES = {
    "master": "cct-pill-master",
    "user": "cct-pill-user",
    "success": "cct-pill-success",
    "warn": "cct-pill-warn",
    "warning": "cct-pill-warn",
    "danger": "cct-pill-danger",
    "error": "cct-pill-danger",
}


def badge(text, tone="user"):
    """Return a small inline status pill (render with st.markdown)."""
    cls = _PILL_TONES.get(str(tone).lower(), "cct-pill-user")
    return f'<span class="cct-pill {cls}">{text}</span>'


def page_header(title, subtitle="", icon=None):
    """Page hero header — a styled replacement for st.title()."""
    icon_html = f'<span class="cct-hero-icon">{icon}</span>' if icon else ""
    sub_html = f'<p class="cct-hero-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="cct-hero">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'{icon_html}<span class="cct-hero-title">{title}</span>'
        f'</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def card(key=None):
    """White surface card container. Usage: `with styles.card(): ...`"""
    return st.container(border=True, key=key or f"cct-card-{next(_card_keys)}")


def brand_block(name="CallCenterTracker", subtitle=""):
    """Sidebar brand/logo block."""
    st.markdown(
        '<div class="cct-brand">'
        '<div class="cct-brand-logo">&#128222;</div>'
        f'<div><div class="cct-brand-name">{name}</div>'
        f'<div class="cct-brand-sub">{subtitle}</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def user_card(name, role="user"):
    """Sidebar user card — avatar, display name and role pill."""
    initial = (str(name) or "?")[:1].upper()
    role_label = str(role or "user").capitalize()
    st.markdown(
        '<div class="cct-user">'
        f'<div class="cct-avatar">{initial}</div>'
        f'<div><div class="cct-user-name">{name}</div>'
        f'{badge(role_label, "master" if str(role).lower() == "master" else "user")}'
        '</div></div>',
        unsafe_allow_html=True,
    )


def login_hero(title="CallCenterTracker", subtitle="Sales Conversion Tracking System"):
    """Centered hero block for the login screen."""
    st.markdown(
        '<div class="cct-login-logo">&#128222;</div>'
        f'<div class="cct-login-title">{title}</div>'
        f'<p class="cct-login-sub">{subtitle}</p>',
        unsafe_allow_html=True,
    )
