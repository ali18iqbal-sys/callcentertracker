"""
targets.py — Target persistence and weighted average calculations.
"""

from pathlib import Path
import yaml
from datetime import date, timedelta
import calendar


TARGETS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "targets.yaml"

DEFAULT_DAILY_TARGETS = {
    "weekday": 500,
    "saturday": 400,
    "sunday": 200,
    "holiday": 100,
}


def load_targets():
    """Load targets.yaml, applying defaults for any missing section."""
    if not TARGETS_FILE.exists():
        return {
            "daily_targets": dict(DEFAULT_DAILY_TARGETS),
            "team_targets": {},
            "dialer_targets": {},
        }

    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Ensure every section is present
    data.setdefault("daily_targets", dict(DEFAULT_DAILY_TARGETS))
    data.setdefault("team_targets", {})
    data.setdefault("dialer_targets", {})

    return data


def save_targets(targets):
    """Write the targets configuration to targets.yaml."""
    TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TARGETS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(targets, f, default_flow_style=False, allow_unicode=True)


def calculate_monthly_target(daily_targets, year=None, month=None):
    """Calculate the monthly call target as a weighted average.

    Returns:
        dict: {
            "weekdays": {"days": N, "per_day": X, "total": Y},
            "saturdays": {"days": N, "per_day": X, "total": Y},
            "sundays": {"days": N, "per_day": X, "total": Y},
            "holidays": {"days": N, "per_day": X, "total": Y},
            "total_target": Z,
            "weighted_avg": W,
            "year": YYYY,
            "month": MM,
        }
    """
    today = date.today()
    year = year or today.year
    month = month or today.month

    days_in_month = calendar.monthrange(year, month)[1]

    weekdays = 0
    saturdays = 0
    sundays = 0
    # Holidays are currently not modelled; a holiday calendar can be added later
    holidays = 0

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        weekday = d.weekday()  # Monday=0, Sunday=6

        if weekday == 5:      # Saturday
            saturdays += 1
        elif weekday == 6:    # Sunday
            sundays += 1
        else:
            weekdays += 1

    wd_target = daily_targets.get("weekday", 500)
    sat_target = daily_targets.get("saturday", 400)
    sun_target = daily_targets.get("sunday", 200)
    hol_target = daily_targets.get("holiday", 100)

    wd_total = weekdays * wd_target
    sat_total = saturdays * sat_target
    sun_total = sundays * sun_target
    hol_total = holidays * hol_target

    total = wd_total + sat_total + sun_total + hol_total
    weighted_avg = round(total / days_in_month, 2) if days_in_month > 0 else 0

    return {
        "weekdays":  {"days": weekdays,  "per_day": wd_target,  "total": wd_total},
        "saturdays": {"days": saturdays, "per_day": sat_target, "total": sat_total},
        "sundays":   {"days": sundays,   "per_day": sun_target, "total": sun_total},
        "holidays":  {"days": holidays,  "per_day": hol_target, "total": hol_total},
        "total_target": total,
        "weighted_avg": weighted_avg,
        "year": year,
        "month": month,
        "days_in_month": days_in_month,
    }