"""Persistent report history (Phase 2).

Every processed upload is recorded in a small SQLite database as *aggregate
snapshots* — per (report metric x company x month) counts. Raw ticket rows are
deliberately NOT stored: history/trends only need the aggregates, and client
ticket detail shouldn't accumulate inside the dashboard's database.

Duplicate uploads (same file bytes) are detected by hash and recorded once.
When the same company-month appears in several uploads (e.g. a re-export with
corrections), queries use the snapshot from the most recent upload.

DB location: $SLA_HISTORY_DB if set, else <repo>/data/history.db. On hosts
with ephemeral disks (Render free tier) history survives restarts but not
redeploys — point SLA_HISTORY_DB at a mounted disk for durability.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .aggregate import ALL, METRICS, _sla_percentage, metric_scope

_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash   TEXT UNIQUE NOT NULL,
    filename    TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    row_count   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    upload_id INTEGER NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    metric    TEXT NOT NULL,
    company   TEXT NOT NULL,
    month     TEXT NOT NULL,
    total     INTEGER NOT NULL,
    within    INTEGER NOT NULL,
    PRIMARY KEY (upload_id, metric, company, month)
);
"""


def db_path() -> Path:
    env = os.environ.get("SLA_HISTORY_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "history.db"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(_SCHEMA)
    return con


def _snapshot_rows(df: pd.DataFrame) -> list[tuple[str, str, str, int, int]]:
    """(metric, company, month, total, within) for every metric x company x month."""
    rows: list[tuple[str, str, str, int, int]] = []
    scoped = df[df["reporting_month"] != ""]
    for metric in METRICS:
        sub, within_m = metric_scope(scoped, metric)
        if sub.empty:
            continue
        g = sub.assign(_within=within_m.astype(int)).groupby(
            ["company_name", "reporting_month"])
        agg = g.agg(total=("ticket_id", "size"), within=("_within", "sum")).reset_index()
        rows += [(metric, r.company_name, r.reporting_month, int(r.total), int(r.within))
                 for r in agg.itertuples()]
    return rows


def record_upload(data: bytes, filename: str, df: pd.DataFrame) -> tuple[int, bool]:
    """Record a processed upload. Returns (upload_id, newly_created)."""
    file_hash = hashlib.sha256(data).hexdigest()
    with _connect() as con:
        existing = con.execute(
            "SELECT id FROM uploads WHERE file_hash = ?", (file_hash,)).fetchone()
        if existing:
            return existing[0], False
        cur = con.execute(
            "INSERT INTO uploads (file_hash, filename, uploaded_at, row_count) "
            "VALUES (?, ?, ?, ?)",
            (file_hash, filename,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), len(df)))
        upload_id = cur.lastrowid
        con.executemany(
            "INSERT INTO snapshots (upload_id, metric, company, month, total, within) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(upload_id, *row) for row in _snapshot_rows(df)])
    return upload_id, True


def uploads() -> pd.DataFrame:
    """All recorded uploads, newest first, with the months/companies they cover."""
    with _connect() as con:
        return pd.read_sql_query(
            """SELECT u.id AS ID, u.filename AS File, u.uploaded_at AS Uploaded,
                      u.row_count AS Tickets,
                      MIN(s.month) || ' – ' || MAX(s.month) AS Months,
                      COUNT(DISTINCT s.company) AS Companies
               FROM uploads u
               LEFT JOIN snapshots s ON s.upload_id = u.id AND s.metric = ?
               GROUP BY u.id ORDER BY u.id DESC""",
            con, params=(next(iter(METRICS)),))


def delete_upload(upload_id: int) -> None:
    with _connect() as con:
        con.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))


def companies() -> list[str]:
    with _connect() as con:
        rows = con.execute("SELECT DISTINCT company FROM snapshots ORDER BY company")
        return [r[0] for r in rows.fetchall()]


# Latest upload wins per (metric, company, month) so re-exports supersede.
_LATEST = """
    FROM snapshots s
    WHERE s.metric = :metric
      AND (:company = :all OR s.company = :company)
      AND s.upload_id = (
          SELECT MAX(s2.upload_id) FROM snapshots s2
          WHERE s2.metric = s.metric AND s2.company = s.company
            AND s2.month = s.month)
"""


def trend(metric: str, company: str = ALL) -> pd.DataFrame:
    """Month-over-month SLA trend across all recorded history."""
    params = {"metric": metric, "company": company, "all": ALL}
    with _connect() as con:
        out = pd.read_sql_query(
            f"""SELECT s.month AS Month, SUM(s.total) AS Total,
                       SUM(s.within) AS "Within SLA" {_LATEST}
                GROUP BY s.month ORDER BY s.month""",
            con, params=params)
    if out.empty:
        return pd.DataFrame(columns=["Month", "Total", "Within SLA", "Outside SLA", "% Within"])
    out["Outside SLA"] = out["Total"] - out["Within SLA"]
    out["% Within"] = (100.0 * out["Within SLA"] / out["Total"]).round(2)
    return out[["Month", "Total", "Within SLA", "Outside SLA", "% Within"]]


def overall(metric: str, company: str = ALL) -> dict:
    """All-time KPIs across recorded history (latest snapshot per company-month)."""
    t = trend(metric, company)
    total = int(t["Total"].sum()) if not t.empty else 0
    within = int(t["Within SLA"].sum()) if not t.empty else 0
    return {
        "months": len(t),
        "total_tickets": total,
        "within_sla": within,
        "outside_sla": total - within,
        "sla_percentage": _sla_percentage(total, within),
    }
