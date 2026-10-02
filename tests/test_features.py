"""
test_features.py — Multi-sheet merge + Ringba fetcher + scheduler tests.

Run from the project root:

    python tests/test_features.py

Also supported with pytest:

    pytest tests/test_features.py
"""

import sys
import tempfile
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

import pandas as pd

# Make the project root importable for standalone runs
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.reader import read_excel, read_file, list_excel_sheets
from app.core import ringba_fetcher as rf
from app.core import scheduler as sch
from app.utils.excel_io import df_to_excel_bytes, sheets_to_excel_bytes


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def _make_multisheet(path):
    """Build a 2-sheet Excel workbook (for the multi-sheet merge tests)."""
    d1 = pd.DataFrame({
        "Phone #": ["03001234567", "03011234567"],
        "Team": ["T1", "T2"],
    })
    d2 = pd.DataFrame({
        "Phone #": ["03021234567", "03031234567", "03041234567"],
        "Team": ["T1", "T3", "T2"],
    })
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        d1.to_excel(w, index=False, sheet_name="Team A")
        d2.to_excel(w, index=False, sheet_name="Team B")
    return d1, d2


class _TempState:
    """Redirect the scheduler state file to a temp directory (test isolation)."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = sch.STATE_FILE
        sch.STATE_FILE = Path(self.tmp.name) / "last_fetch.json"
        return sch

    def __exit__(self, *exc):
        sch.STATE_FILE = self._orig
        self.tmp.cleanup()
        return False


class _FakeResponse:
    """requests.Response ka minimal stand-in."""

    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise rf.requests.HTTPError(f"HTTP {self.status_code}")


class _FakeSession:
    """Stand-in for requests.Session that records the calls it receives."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({
            "url": url, "headers": headers, "json": json, "timeout": timeout,
        })
        if not self._responses:
            raise AssertionError("Unexpected extra Ringba request")
        return self._responses.pop(0)


# ═══════════════════════════════════════════════════════════
#  TESTS — Excel multi-sheet merging
# ═══════════════════════════════════════════════════════════
def test_multisheet_merge_combines_all_sheets():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cc_multi.xlsx"
        d1, d2 = _make_multisheet(path)

        combined = read_excel(path)

        assert len(combined) == len(d1) + len(d2), "Saari sheets merge honi chahiye"
        assert "_source_sheet" in combined.columns
        assert set(combined["_source_sheet"].unique()) == {"Team A", "Team B"}
        assert list(list_excel_sheets(path)) == ["Team A", "Team B"]


def test_multisheet_merge_meta_and_read_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "client_multi.xlsx"
        _make_multisheet(path)

        df, meta = read_excel(path, return_meta=True)
        assert meta["n_sheets"] == 2, meta
        assert len(df) == 5

        df2 = read_file(path, path.name)  # auto type-detect
        assert len(df2) == 5


def test_multisheet_skips_empty_and_blank_sheets():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "with_blank.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            pd.DataFrame({"Phone #": ["03001234567"]}).to_excel(
                w, index=False, sheet_name="Data")
            pd.DataFrame({"Phone #": [None]}).to_excel(
                w, index=False, sheet_name="Blank")
            pd.DataFrame().to_excel(w, index=False, sheet_name="Empty")

        df = read_excel(path)
        assert len(df) == 1, "Empty and blank sheets should be skipped"


def test_single_sheet_compatibility():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.xlsx"
        pd.DataFrame({"Phone #": ["03001234567", "03011234567"]}).to_excel(
            path, index=False, sheet_name="Sheet1")
        df = read_excel(path, sheet_name="Sheet1")
        assert len(df) == 2


def test_consolidated_sheet_excel_export():
    df = pd.DataFrame({
        "phone": ["03001234567", "03011234567"],
        "amount": [100, 200],
    })
    blob = df_to_excel_bytes(df, "Consolidated")
    assert isinstance(blob, (bytes, bytearray)) and len(blob) > 0

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "out.xlsx"
        p.write_bytes(blob)
        back = pd.read_excel(p, sheet_name="Consolidated")
        assert len(back) == 2

    multi = sheets_to_excel_bytes({"A": df, "B": df})
    assert isinstance(multi, (bytes, bytearray)) and len(multi) > 0


# ═══════════════════════════════════════════════════════════
#  TESTS — Ringba fetcher
# ═══════════════════════════════════════════════════════════
def test_ringba_auth_body_and_pagination():
    page1 = {"report": {"records": [
        {"inboundPhoneNumber": "03001234567"},
        {"inboundPhoneNumber": "03001234568"},
    ], "recordCount": 3}}
    page2 = {"report": {"records": [
        {"inboundPhoneNumber": "03001234569"},
    ], "recordCount": 3}}

    sess = _FakeSession([_FakeResponse(page1), _FakeResponse(page2)])
    df = rf.fetch_ringba_calls(
        "ACC1", "tok123",
        "2026-02-01T00:00:00Z", "2026-02-02T00:00:00Z",
        page_size=2, session=sess,
    )

    assert len(df) == 3
    assert df.attrs["ringba_pages"] == 2
    assert len(sess.calls) == 2, "Do page requests expected"

    c0 = sess.calls[0]
    assert c0["url"] == "https://api.ringba.com/v2/ACC1/calllogs"
    assert c0["headers"]["Authorization"] == "Token tok123"
    assert c0["json"]["size"] == 2
    assert c0["json"]["offset"] == 0
    assert c0["json"]["reportStart"] == "2026-02-01T00:00:00Z"
    assert sess.calls[1]["json"]["offset"] == 2, "Offset page_size se barhna chahiye"


def test_ringba_calllog_data_envelope():
    payload = {"callLog": {"data": [
        {"callerId": "03001234567", "callLengthInSeconds": 90},
    ]}}
    sess = _FakeSession([_FakeResponse(payload)])
    df = rf.fetch_ringba_calls("A", "t", None, None, page_size=50, session=sess)
    assert len(df) == 1
    assert df.iloc[0]["callerId"] == "03001234567"


def test_ringba_extract_records_shapes():
    assert rf._extract_records([{"a": 1}]) == [{"a": 1}]
    assert rf._extract_records({"records": [{"a": 1}]}) == [{"a": 1}]
    assert rf._extract_records({"data": [{"a": 2}]}) == [{"a": 2}]
    assert rf._extract_records({"report": {"records": [{"a": 3}]}}) == [{"a": 3}]
    assert rf._extract_records({"callLog": {"data": [{"a": 4}]}}) == [{"a": 4}]
    assert rf._extract_records({"nothing": 1}) == []


def test_ringba_iso_conversion():
    assert rf._iso(date(2026, 2, 3)) == "2026-02-03T00:00:00Z"
    assert rf._iso(datetime(2026, 2, 3, 5, 30)) == "2026-02-03T05:30:00Z"
    assert rf._iso("2026-02-03T00:00:00Z") == "2026-02-03T00:00:00Z"
    assert rf._iso(None) is None


def test_ringba_401_error_mapping():
    sess = _FakeSession([_FakeResponse({}, status_code=401, text="Unauthorized")])
    try:
        rf.fetch_ringba_calls("A", "bad-token", None, None, session=sess)
        raise AssertionError("RingbaError expected")
    except rf.RingbaError as exc:
        assert "401" in str(exc)


def test_ringba_requires_credentials():
    for kwargs in [{"account_id": "", "api_token": "x"},
                   {"account_id": "A", "api_token": ""}]:
        try:
            rf.fetch_ringba_calls(
                report_start=None, report_end=None,
                session=_FakeSession([]), **kwargs,
            )
            raise AssertionError("RingbaError expected")
        except rf.RingbaError:
            pass


def test_normalize_ringba_maps_fields():
    raw = pd.DataFrame([{
        "inboundPhoneNumber": "03001234567",
        "callDt": "2026-02-10T10:00:00Z",
        "callLengthInSeconds": 120,
        "campaignName": "C1",
        "targetName": "D1",
        "inboundCallId": "abc123",
    }])
    out = rf.normalize_ringba(raw)
    row = out.iloc[0]
    assert row["phone"] == "03001234567"
    assert row["team"] == "C1"
    assert row["dialer"] == "D1"
    assert round(float(row["minutes"]), 2) == 2.0
    assert int(row["calls"]) == 1
    assert row["ringba_call_id"] == "abc123"


def test_normalize_ringba_empty():
    out = rf.normalize_ringba(pd.DataFrame())
    assert "phone" in out.columns
    assert len(out) == 0


# ═══════════════════════════════════════════════════════════
#  TESTS — Scheduler / timer
# ═══════════════════════════════════════════════════════════
def test_scheduler_interval_due():
    sched = {"enabled": True, "mode": "interval", "interval_minutes": 60}
    now = datetime(2026, 2, 10, 12, 0)

    assert sch.is_due(sched, now=now, last_run=now - timedelta(minutes=90)) is True
    assert sch.is_due(sched, now=now, last_run=now - timedelta(minutes=10)) is False
    assert sch.is_due({**sched, "enabled": False}, now=now,
                      last_run=now - timedelta(minutes=90)) is False


def test_scheduler_first_run_behaviour():
    now = datetime(2026, 2, 10, 12, 0)
    sched = {"enabled": True, "mode": "interval",
             "interval_minutes": 60, "run_on_start": True}
    with _TempState():
        assert sch.is_due(sched, now=now, last_run=None) is True
        assert sch.is_due({**sched, "run_on_start": False},
                          now=now, last_run=None) is False


def test_scheduler_times_due():
    sched = {"enabled": True, "mode": "times", "times": ["09:00", "13:00"]}
    now = datetime(2026, 2, 10, 14, 0)

    assert sch.is_due(sched, now=now, last_run=datetime(2026, 2, 10, 8, 0)) is True
    assert sch.is_due(sched, now=now, last_run=datetime(2026, 2, 10, 13, 30)) is False
    assert sch.is_due(sched, now=datetime(2026, 2, 10, 8, 0),
                      last_run=datetime(2026, 2, 10, 7, 0)) is False


def test_scheduler_next_run_time():
    now = datetime(2026, 2, 10, 14, 0)

    times_sched = {"enabled": True, "mode": "times", "times": ["09:00", "13:00"]}
    assert sch.next_run_time(times_sched, now=now) == datetime(2026, 2, 11, 9, 0)

    interval_sched = {"enabled": True, "mode": "interval", "interval_minutes": 60}
    with _TempState():
        sch.set_last_run(datetime(2026, 2, 10, 13, 30))
        assert sch.next_run_time(interval_sched, now=now) == datetime(2026, 2, 10, 14, 30)

    assert sch.next_run_time({**times_sched, "enabled": False}, now=now) is None


def test_parse_time():
    assert sch.parse_time("09:00") == dtime(9, 0)
    assert sch.parse_time("23:59:59") == dtime(23, 59, 59)
    assert sch.parse_time("bad") is None
    assert sch.parse_time("99:00") is None
    assert sch.parse_time(dtime(6, 15)) == dtime(6, 15)


def test_state_roundtrip():
    with _TempState():
        assert sch.get_last_run() is None
        sch.set_last_run(datetime(2026, 2, 10, 12, 0), extra={"ok": True})
        assert sch.get_last_run() == datetime(2026, 2, 10, 12, 0)
        assert sch.get_state().get("ok") is True
        sch.reset_state()
        assert sch.get_last_run() is None


def test_schedule_load_save_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        orig = sch.SCHEDULE_FILE
        try:
            sch.SCHEDULE_FILE = Path(tmp) / "schedule.yaml"
            sched = sch.load_schedule()
            assert sched["mode"] == "interval"
            assert sched["enabled"] is False
            assert "interval_minutes" in sched

            sched["enabled"] = True
            sched["interval_minutes"] = 15
            sch.save_schedule(sched)

            again = sch.load_schedule()
            assert again["enabled"] is True
            assert again["interval_minutes"] == 15
        finally:
            sch.SCHEDULE_FILE = orig


def test_source_selected_filter():
    assert sch._source_selected({"sources": []}, "anything") is True
    assert sch._source_selected({"sources": ["A"]}, "A") is True
    assert sch._source_selected({"sources": ["A"]}, "B") is False


def test_fetch_enabled_sources_empty():
    import app.core.sources_manager as sm
    orig = sm.SOURCES_FILE
    with tempfile.TemporaryDirectory() as tmp:
        try:
            sm.SOURCES_FILE = Path(tmp) / "sources.yaml"  # nicht existent
            out = sch.fetch_enabled_sources(schedule={"sources": []})
            assert len(out["client"]) == 0
            assert len(out["cc"]) == 0
            assert out["results"] == []
        finally:
            sm.SOURCES_FILE = orig


def test_end_to_end_multisheet_merge_into_match():
    """Multi-sheet CC + single-sheet client → normalize → match."""
    from app.config import get
    from app.pages.upload_page import normalize_single_file
    from app.core.matcher import match_data

    col_config = get("columns", {})

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        # CC file: 2 sheets (team-wise split) — must merge to 3 rows
        cc_path = tmpdir / "cc.xlsx"
        with pd.ExcelWriter(cc_path, engine="openpyxl") as w:
            pd.DataFrame({
                "Phone #": ["03001234567", "03011234567"],
                "Team": ["T1", "T1"],
            }).to_excel(w, index=False, sheet_name="T1")
            pd.DataFrame({
                "Phone #": ["03021234567"],
                "Team": ["T2"],
            }).to_excel(w, index=False, sheet_name="T2")

        # Client file: 1 sheet, 2 sales
        cl_path = tmpdir / "client.xlsx"
        pd.DataFrame({
            "Phone Number": ["03001234567", "03021234567"],
            "Price": [500, 300],
            "Amount": [5000, 3000],
        }).to_excel(cl_path, index=False, sheet_name="Sales")

        cc_raw = read_file(cc_path, cc_path.name)
        cl_raw = read_file(cl_path, cl_path.name)
        assert len(cc_raw) == 3, "CC ki dono sheets merge honi chahiye"
        assert len(cl_raw) == 2
        assert set(cc_raw["_source_sheet"].unique()) == {"T1", "T2"}

        cc_norm, err1 = normalize_single_file(cc_raw, col_config, "cc.xlsx")
        cl_norm, err2 = normalize_single_file(cl_raw, col_config, "client.xlsx")
        assert err1 is None and err2 is None, (err1, err2)

        result = match_data(cl_norm, cc_norm)
        summary = result["summary"]

        assert summary["sold_rows"] == 2, summary
        assert summary["no_sale_rows"] == 1, summary
        assert summary["orphan_rows"] == 0, summary


# ═══════════════════════════════════════════════════════════
#  TESTS — End-to-end job runner
# ═══════════════════════════════════════════════════════════
def test_run_fetch_job_integration_consolidates_and_saves():
    import app.core.sources_manager as sm
    import app.core.api_fetcher as af

    orig_sources = sm.SOURCES_FILE
    orig_state = sch.STATE_FILE
    orig_fetched = sch.FETCHED_DIR
    orig_fetch_api = af.fetch_api

    tmp = tempfile.TemporaryDirectory()
    try:
        tmpdir = Path(tmp.name)
        sm.SOURCES_FILE = tmpdir / "sources.yaml"
        sm.save_sources({
            "google_sheets": [],
            "apis": [{
                "name": "FakeAPI", "url": "http://x", "type": "cc",
                "auth_type": "none", "auth_value": "", "json_path": "",
                "enabled": True,
            }],
            "ringba": [],
        })
        sch.STATE_FILE = tmpdir / "last_fetch.json"
        sch.FETCHED_DIR = tmpdir / "fetched"

        # Network bypass — fake fetch
        af.fetch_api = lambda **kwargs: pd.DataFrame({"phone": ["03001234567"]})

        outcome = sch.run_fetch_job(
            schedule={"persist_to_disk": True},
            now=datetime(2026, 2, 10, 12, 0),
        )

        assert outcome["cc_rows"] == 1
        assert outcome["results"][0]["ok"] is True
        assert "cc" in outcome["saved"]
        assert Path(outcome["saved"]["cc"]).exists()
        assert sch.get_last_run() == datetime(2026, 2, 10, 12, 0)
    finally:
        af.fetch_api = orig_fetch_api
        sm.SOURCES_FILE = orig_sources
        sch.STATE_FILE = orig_state
        sch.FETCHED_DIR = orig_fetched
        tmp.cleanup()


def test_run_scheduler_daemon_once_smoke():
    import app.core.sources_manager as sm
    import run_scheduler

    orig_sources = sm.SOURCES_FILE
    orig_state = sch.STATE_FILE
    orig_sched = sch.SCHEDULE_FILE

    tmp = tempfile.TemporaryDirectory()
    try:
        tmpdir = Path(tmp.name)
        sm.SOURCES_FILE = tmpdir / "sources.yaml"   # no sources configured
        sch.STATE_FILE = tmpdir / "last_fetch.json"
        sch.SCHEDULE_FILE = tmpdir / "schedule.yaml"

        did_run = run_scheduler._run_once(force=True, days=1)
        assert did_run is True
        assert sch.get_last_run() is not None
    finally:
        sm.SOURCES_FILE = orig_sources
        sch.STATE_FILE = orig_state
        sch.SCHEDULE_FILE = orig_sched
        tmp.cleanup()


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
    print("  CallCenterTracker — Feature Tests")
    print("=" * 60)

    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {t.__name__}: {exc}")
            import traceback
            traceback.print_exc()
            failed.append(t.__name__)

    print("-" * 60)
    print(f"  {passed}/{len(tests)} tests passed")
    if failed:
        print("  Failed: " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()


