"""Aggregation layer: turn the standardised per-ticket frame into KPIs.

Produces the exact Phase 1 output contract from the brief:
    {"company", "month", "total_tickets", "within_sla", "outside_sla", "sla_percentage"}
"""
from __future__ import annotations

import pandas as pd

from .sla_engine import applicable_mask, within_mask

ALL = "All"

# Report types: metric label -> status fields it covers (None = the combined
# rule across all configured fields, i.e. the Phase 1 behaviour).
COMBINED = "Combined SLA"
METRICS: dict[str, list[str] | None] = {
    COMBINED: None,
    "First response": ["first_response_status"],
    "Resolution": ["resolution_status"],
    "Every response": ["every_response_status"],
}


def _sla_percentage(total: int, within: int) -> float:
    return round(100.0 * within / total, 2) if total else 0.0


def metric_scope(df: pd.DataFrame, metric: str | None) -> tuple[pd.DataFrame, pd.Series]:
    """Return (rows in scope for this report type, within-SLA mask for them).

    Combined: every ticket is in scope (blank statuses count as no breach —
    the Phase 1 rule). Per-metric: only tickets that actually carried that SLA
    target (status populated), judged on that field alone.
    """
    fields = METRICS.get(metric or COMBINED)
    if fields is None:
        return df, df["sla_within_flag"] == "Y"
    sub = df[applicable_mask(df, fields)]
    return sub, within_mask(sub, fields)


def filter_frame(df: pd.DataFrame, company: str | None = None,
                 month: str | None = None) -> pd.DataFrame:
    out = df
    if company and company != ALL:
        out = out[out["company_name"] == company]
    if month and month != ALL:
        out = out[out["reporting_month"] == month]
    return out


def kpi(df: pd.DataFrame, company: str | None = None,
        month: str | None = None, metric: str | None = None) -> dict:
    """Core KPI output for the selected filters and report type."""
    sub = filter_frame(df, company, month)
    sub, within_m = metric_scope(sub, metric)
    total = len(sub)
    within = int(within_m.sum())
    return {
        "company": company or ALL,
        "month": month or ALL,
        "metric": metric or COMBINED,
        "total_tickets": total,
        "within_sla": within,
        "outside_sla": total - within,
        "sla_percentage": _sla_percentage(total, within),
    }


def list_companies(df: pd.DataFrame) -> list[str]:
    return sorted(df["company_name"].dropna().unique().tolist())


def list_months(df: pd.DataFrame) -> list[str]:
    vals = [m for m in df["reporting_month"].dropna().unique().tolist() if m]
    return sorted(vals)


def by_company(df: pd.DataFrame, month: str | None = None,
               metric: str | None = None) -> pd.DataFrame:
    """Per-company breakdown table (mirrors the manual 'SLA by Customer' reports)."""
    sub = filter_frame(df, month=month)
    sub, within_m = metric_scope(sub, metric)
    if sub.empty:
        return pd.DataFrame(columns=["Company", "Total", "Within SLA", "Outside SLA", "% Within"])
    g = sub.assign(_within=within_m.astype(int))
    agg = g.groupby("company_name").agg(
        Total=("ticket_id", "size"),
        Within_SLA=("_within", "sum"),
    ).reset_index()
    agg["Outside SLA"] = agg["Total"] - agg["Within_SLA"]
    agg["% Within"] = (100.0 * agg["Within_SLA"] / agg["Total"]).round(2)
    agg = agg.rename(columns={"company_name": "Company", "Within_SLA": "Within SLA"})
    return agg[["Company", "Total", "Within SLA", "Outside SLA", "% Within"]].sort_values(
        "Total", ascending=False, ignore_index=True)


def by_month(df: pd.DataFrame, company: str | None = None,
             metric: str | None = None) -> pd.DataFrame:
    """Month-over-month trend (Phase 2 groundwork, cheap to expose now)."""
    sub = filter_frame(df, company=company)
    sub = sub[sub["reporting_month"] != ""]
    sub, within_m = metric_scope(sub, metric)
    if sub.empty:
        return pd.DataFrame(columns=["Month", "Total", "Within SLA", "Outside SLA", "% Within"])
    g = sub.assign(_within=within_m.astype(int))
    agg = g.groupby("reporting_month").agg(
        Total=("ticket_id", "size"),
        Within_SLA=("_within", "sum"),
    ).reset_index()
    agg["Outside SLA"] = agg["Total"] - agg["Within_SLA"]
    agg["% Within"] = (100.0 * agg["Within_SLA"] / agg["Total"]).round(2)
    agg = agg.rename(columns={"reporting_month": "Month", "Within_SLA": "Within SLA"})
    return agg[["Month", "Total", "Within SLA", "Outside SLA", "% Within"]].sort_values(
        "Month", ignore_index=True)
