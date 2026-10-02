"""
run_scheduler.py — Standalone auto-fetch daemon.

Runs in the background and fetches data according to data/schedule.yaml, either
at a fixed interval or at specific times of day.

Usage (from the project root):

    python run_scheduler.py                  # check every 60 seconds (default)
    python run_scheduler.py --poll 30        # check every 30 seconds
    python run_scheduler.py --once           # perform a single due check, then exit
    python run_scheduler.py --force          # ignore the schedule and fetch now
    python run_scheduler.py --days 3         # Ringba report window in days

It can also be driven by Windows Task Scheduler or cron using --once.
"""

import argparse
import time
from datetime import datetime

from app.core import scheduler


def _print(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _run_once(force=False, days=None):
    """Run the fetch job if it is due (or unconditionally when forced)."""
    if force:
        outcome = scheduler.run_fetch_job(ringba_report_days=days)
    else:
        outcome = scheduler.maybe_run_due(ringba_report_days=days)

    if outcome is None:
        _print("Not due yet — no action taken.")
        return False

    _print(
        f"Job completed: client={outcome['client_rows']} rows, "
        f"cc={outcome['cc_rows']} rows"
    )
    for result in outcome["results"]:
        mark = "OK " if result.get("ok") else "ERR"
        extra = "" if result.get("ok") else f" — {result.get('error', '')}"
        _print(
            f"  [{mark}] {result.get('source')} ({result.get('kind')}): "
            f"{result.get('rows')} rows{extra}"
        )
    if outcome.get("saved"):
        for kind, path in outcome["saved"].items():
            _print(f"  saved {kind} → {path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="CallCenterTracker auto-fetch timer")
    parser.add_argument("--poll", type=int, default=60,
                        help="Check interval in seconds (default 60)")
    parser.add_argument("--once", action="store_true",
                        help="Perform a single due check and exit")
    parser.add_argument("--force", action="store_true",
                        help="Ignore the schedule and fetch immediately")
    parser.add_argument("--days", type=int, default=None,
                        help="Ringba report window in days")
    args = parser.parse_args()

    sched = scheduler.load_schedule()
    _print(
        f"Schedule: enabled={sched.get('enabled')} mode={sched.get('mode')} "
        f"interval={sched.get('interval_minutes')}m times={sched.get('times')}"
    )

    if args.once or args.force:
        _run_once(force=args.force, days=args.days)
        return

    if not sched.get("enabled"):
        _print("⚠️  The schedule is disabled (set 'enabled: true' in "
               "data/schedule.yaml). The daemon will still run.")

    poll = max(5, int(args.poll))
    _print(f"Daemon started — checking every {poll}s. Press Ctrl+C to stop.")
    try:
        while True:
            _run_once(force=False, days=args.days)
            time.sleep(poll)
    except KeyboardInterrupt:
        _print("Daemon stopped (Ctrl+C).")


if __name__ == "__main__":
    main()