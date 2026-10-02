"""
scheduler.py — Auto-fetch timer and scheduling engine.

Two modes are supported:
    interval : fetch every N minutes (e.g. 30)
    times    : fetch at specific times of day (e.g. "09:00", "13:00")

Files:
    data/schedule.yaml    → schedule configuration
    data/last_fetch.json  → state of the last run
    data/fetched/         → fetched data (cc_latest.xlsx / client_latest.xlsx)

This module is used both from inside Streamlit (Schedule tab) and from the
standalone daemon (run_scheduler.py).
"""

import json
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).parent.parent.parent
SCHEDULE_FILE = ROOT_DIR / "data" / "schedule.yaml"
STATE_FILE = ROOT_DIR / "data" / "last_fetch.json"
FETCHED_DIR = ROOT_DIR / "data" / "fetched"


DEFAULT_SCHEDULE = {
    "enabled": False,
    "mode": "interval",          # 'interval' or 'times'
    "interval_minutes": 60,
    "times": ["09:00", "13:00", "18:00"],
    "sources": [],               # empty means every enabled source
    "run_on_start": True,        # run immediately if it has never run before
    "persist_to_disk": True,     # save fetched data under data/fetched/
}


# ─────────────── Config load / save ───────────────
def load_schedule():
    """Load schedule.yaml, merged over the defaults."""
    sched = dict(DEFAULT_SCHEDULE)
    if SCHEDULE_FILE.exists():
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}
        if isinstance(data, dict):
            # Also support a nested "schedule:" key
            if isinstance(data.get("schedule"), dict):
                data = data["schedule"]
            sched.update({k: v for k, v in data.items() if v is not None})
    return sched


def save_schedule(schedule):
    """Write the schedule configuration to schedule.yaml."""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        yaml.dump(
            schedule, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    return schedule


# ─────────────── Time helpers ───────────────
def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_time(value):
    """Parse '09:00' / '09:00:00' / a time object into a datetime.time, or None."""
    if isinstance(value, dtime):
        return value
    if isinstance(value, str):
        parts = value.strip().split(":")
        try:
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
            ss = int(parts[2]) if len(parts) > 2 else 0
            if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59:
                return dtime(hh, mm, ss)
        except (ValueError, IndexError):
            return None
    return None


def parse_times(times):
    """Convert a list of time strings into sorted time objects."""
    out = []
    for t in times or []:
        parsed = parse_time(t)
        if parsed is not None:
            out.append(parsed)
    return sorted(out)


def _last_scheduled_dt(schedule, now):
    """Return the most recent scheduled datetime before ``now`` (times mode)."""
    slots = parse_times(schedule.get("times"))
    if not slots:
        return None
    candidates = []
    for day_offset in (0, -1):
        day = (now + timedelta(days=day_offset)).date()
        for slot in slots:
            dt = datetime.combine(day, slot)
            if dt <= now:
                candidates.append(dt)
    return max(candidates) if candidates else None


def is_due(schedule=None, now=None, last_run=None):
    """Determine whether an automatic fetch is due.

    interval mode : last_run + interval_minutes <= now
    times mode    : a scheduled slot after last_run has already passed
    """
    schedule = schedule or load_schedule()
    if not schedule.get("enabled"):
        return False

    now = now or datetime.now()
    if last_run is None:
        last_run = get_last_run()

    # First run (no state recorded yet)
    if last_run is None:
        return bool(schedule.get("run_on_start", True))

    mode = str(schedule.get("mode", "interval")).lower()

    if mode == "interval":
        minutes = max(1, _safe_int(schedule.get("interval_minutes"), 60))
        return (now - last_run) >= timedelta(minutes=minutes)

    if mode == "times":
        slot = _last_scheduled_dt(schedule, now)
        if slot is None:
            return False
        return last_run < slot

    return False


def next_run_time(schedule=None, now=None):
    """Return when the next scheduled run is due, or None when disabled."""
    schedule = schedule or load_schedule()
    if not schedule.get("enabled"):
        return None

    now = now or datetime.now()
    mode = str(schedule.get("mode", "interval")).lower()

    if mode == "interval":
        minutes = max(1, _safe_int(schedule.get("interval_minutes"), 60))
        last_run = get_last_run()
        if last_run is None:
            return now
        nxt = last_run + timedelta(minutes=minutes)
        return nxt if nxt > now else now

    if mode == "times":
        slots = parse_times(schedule.get("times"))
        if not slots:
            return None
        for day_offset in (0, 1, 2):
            day = (now + timedelta(days=day_offset)).date()
            for slot in slots:
                dt = datetime.combine(day, slot)
                if dt > now:
                    return dt
        return None

    return None


# ─────────────── State (last run) ───────────────
def get_last_run():
    """Return the datetime of the last run, or None if it has never run."""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        ts = data.get("last_run")
        return datetime.fromisoformat(ts) if ts else None
    except Exception:
        return None


def get_state():
    """Poora state dict do (last_run + results)."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_last_run(when=None, extra=None):
    """Update last_run in the state file."""
    when = when or datetime.now()
    payload = {"last_run": when.isoformat()}
    if extra:
        payload.update(extra)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return when


def reset_state():
    """Delete the state file, making the next run due again."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ─────────────── Job runner ───────────────
def _source_selected(schedule, name):
    """True when a source is included in the schedule (an empty list means all)."""
    wanted = schedule.get("sources") or []
    if not wanted:
        return True
    return name in wanted


def fetch_enabled_sources(schedule=None, ringba_report_days=None, timeout=60):
    """Fetch every enabled source (Google Sheets / APIs / Ringba).

    Returns:
        {"client": DataFrame, "cc": DataFrame, "results": [dict, ...]}
    """
    import pandas as pd
    from app.core.sources_manager import load_sources, resolve_ringba_credentials
    from app.core.gsheet_fetcher import fetch_gsheet
    from app.core.api_fetcher import fetch_api
    from app.core.ringba_fetcher import fetch_ringba_calls, normalize_ringba

    schedule = schedule or load_schedule()
    sources = load_sources()

    days = _safe_int(ringba_report_days, 1)
    if days is None or days < 0:
        days = 1
    today = date.today()
    report_start = today - timedelta(days=days)
    report_end = today

    buckets = {"client": [], "cc": []}
    results = []

    def _add(kind, df, label):
        kind = "client" if kind == "client" else "cc"
        df = df.copy()
        df["_source_file"] = f"[Auto] {label}"
        buckets[kind].append(df)

    # ─── Google Sheets ───
    for src in sources.get("google_sheets", []):
        name = src.get("name", "gsheet")
        if not src.get("enabled", True) or not _source_selected(schedule, name):
            continue
        try:
            df = fetch_gsheet(
                src.get("url"),
                src.get("credential_file"),
                src.get("sheet_name") or None,
            )
            _add(src.get("type"), df, name)
            results.append({"source": name, "kind": src.get("type"), "rows": len(df), "ok": True})
        except Exception as exc:
            results.append({"source": name, "kind": src.get("type"),
                            "rows": 0, "ok": False, "error": str(exc)[:300]})

    # ─── APIs ───
    for src in sources.get("apis", []):
        name = src.get("name", "api")
        if not src.get("enabled", True) or not _source_selected(schedule, name):
            continue
        try:
            df = fetch_api(
                url=src.get("url"),
                auth_type=src.get("auth_type", "none"),
                auth_value=src.get("auth_value"),
                json_path=src.get("json_path") or None,
                timeout=timeout,
            )
            _add(src.get("type"), df, name)
            results.append({"source": name, "kind": src.get("type"), "rows": len(df), "ok": True})
        except Exception as exc:
            results.append({"source": name, "kind": src.get("type"),
                            "rows": 0, "ok": False, "error": str(exc)[:300]})

    # ─── Ringba ───
    for src in sources.get("ringba", []):
        name = src.get("name", "ringba")
        if not src.get("enabled", True) or not _source_selected(schedule, name):
            continue
        try:
            # Credentials may come from the registry, the environment, or secrets
            account_id, api_token = resolve_ringba_credentials(src)
            raw = fetch_ringba_calls(
                account_id=account_id,
                api_token=api_token,
                report_start=report_start,
                report_end=report_end,
                timeout=timeout,
            )
            df = normalize_ringba(raw)
            _add(src.get("data_type", "cc"), df, name)
            results.append({"source": name, "kind": src.get("data_type", "cc"), "rows": len(df), "ok": True})
        except Exception as exc:
            results.append({"source": name, "kind": src.get("data_type", "cc"),
                            "rows": 0, "ok": False, "error": str(exc)[:300]})

    def _combine(frames):
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True, sort=False)

    return {
        "client": _combine(buckets["client"]),
        "cc": _combine(buckets["cc"]),
        "results": results,
    }


def run_fetch_job(schedule=None, ringba_report_days=None, timeout=60,
                  save_to_disk=None, now=None):
    """Run a fetch job: fetch sources → consolidate → save to disk → update state.

    Returns:
        dict: {ran_at, results, client_rows, cc_rows, saved, ok}
    """
    from app.utils.excel_io import df_to_excel_bytes

    schedule = schedule or load_schedule()
    if save_to_disk is None:
        save_to_disk = bool(schedule.get("persist_to_disk", True))

    outcome = fetch_enabled_sources(
        schedule=schedule, ringba_report_days=ringba_report_days, timeout=timeout
    )
    client_df = outcome["client"]
    cc_df = outcome["cc"]
    results = outcome["results"]

    saved = {}
    if save_to_disk:
        FETCHED_DIR.mkdir(parents=True, exist_ok=True)
        if len(cc_df):
            path = FETCHED_DIR / "cc_latest.xlsx"
            path.write_bytes(df_to_excel_bytes(cc_df, "CC"))
            saved["cc"] = str(path)
        if len(client_df):
            path = FETCHED_DIR / "client_latest.xlsx"
            path.write_bytes(df_to_excel_bytes(client_df, "Client"))
            saved["client"] = str(path)

    run_at = now or datetime.now()
    ok_any = any(r.get("ok") for r in results)
    # last_run is always updated — otherwise a broken source would retry on every poll
    set_last_run(run_at, extra={"results": results, "ok": ok_any})

    return {
        "ran_at": run_at.isoformat(),
        "results": results,
        "client_rows": len(client_df),
        "cc_rows": len(cc_df),
        "saved": saved,
        "ok": ok_any,
    }


def maybe_run_due(now=None, **kwargs):
    """Run the job if it is due, otherwise return None (used by the daemon and the UI)."""
    schedule = load_schedule()
    if not is_due(schedule, now=now):
        return None
    return run_fetch_job(schedule=schedule, now=now, **kwargs)
