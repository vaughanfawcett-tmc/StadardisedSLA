"""Phase 2 tests: per-metric report types and the persistent history store."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from sla_core import COMBINED, METRICS, kpi, by_month  # noqa: E402
from sla_core.sla_engine import derive_sla  # noqa: E402
from sla_core import history  # noqa: E402


def _frame() -> pd.DataFrame:
    df = pd.DataFrame({
        "ticket_id": ["1", "2", "3", "4"],
        "company_name": ["Mitie", "Mitie", "HSBC", "HSBC"],
        "reporting_month": ["2026-05", "2026-05", "2026-05", "2026-06"],
        #                     ok           frs-breach   res-only     blank frs
        "first_response_status": ["Within SLA", "SLA Violated", "", ""],
        "resolution_status": ["Within SLA", "Within SLA", "SLA Violated", "Within SLA"],
        "every_response_status": ["", "", "", ""],
    })
    return derive_sla(df)


def test_combined_metric_matches_phase1_rule():
    r = kpi(_frame(), metric=COMBINED)
    assert (r["total_tickets"], r["within_sla"], r["outside_sla"]) == (4, 2, 2)
    assert r["metric"] == COMBINED


def test_per_metric_scopes_to_applicable_tickets():
    # Only tickets 1 and 2 carry a first-response target; ticket 2 breached it.
    r = kpi(_frame(), metric="First response")
    assert (r["total_tickets"], r["within_sla"], r["outside_sla"]) == (2, 1, 1)
    # Tickets 1, 2, 3, 4 all carry resolution; only ticket 3 breached.
    r = kpi(_frame(), metric="Resolution")
    assert (r["total_tickets"], r["within_sla"]) == (4, 3)
    # Nothing carries an every-response target.
    r = kpi(_frame(), metric="Every response")
    assert r["total_tickets"] == 0 and r["sla_percentage"] == 0.0


def test_by_month_respects_metric():
    t = by_month(_frame(), metric="First response")
    assert t["Month"].tolist() == ["2026-05"]  # 2026-06 ticket has no frs target
    assert int(t["Total"].iloc[0]) == 2


def test_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SLA_HISTORY_DB", str(tmp_path / "history.db"))
    df = _frame()

    up_id, created = history.record_upload(b"file-one", "may.csv", df)
    assert created
    # Same bytes again → deduped.
    up_id2, created2 = history.record_upload(b"file-one", "may-copy.csv", df)
    assert up_id2 == up_id and not created2

    ups = history.uploads()
    assert len(ups) == 1 and int(ups["Tickets"].iloc[0]) == 4

    t = history.trend(COMBINED)
    assert t["Month"].tolist() == ["2026-05", "2026-06"]
    assert int(t["Total"].sum()) == 4 and int(t["Within SLA"].sum()) == 2

    # A re-export covering 2026-05 supersedes the old snapshot for that month.
    df2 = df.copy()
    df2.loc[df2["ticket_id"] == "2", "first_response_status"] = "Within SLA"
    df2 = derive_sla(df2.drop(columns=["sla_within_flag", "sla_status"]))
    history.record_upload(b"file-two", "may-corrected.csv", df2)
    t = history.trend(COMBINED)
    may = t[t["Month"] == "2026-05"].iloc[0]
    assert int(may["Within SLA"]) == 2  # ticket 2 no longer a breach

    # Company filter + overall.
    o = history.overall(COMBINED, "HSBC")
    assert o["total_tickets"] == 2 and o["outside_sla"] == 1

    # Deleting the corrective upload falls back to the original snapshot.
    ups = history.uploads()
    history.delete_upload(int(ups["ID"].iloc[0]))
    t = history.trend(COMBINED)
    assert int(t[t["Month"] == "2026-05"]["Within SLA"].iloc[0]) == 1
