"""Standardised SLA Automation — Phase 1 (Core SLA Reporting / MVP).

Upload a Fresh SLA export (CSV/XLSX) → filter by company + month → SLA KPIs.
The UI is a thin layer over ``sla_core``; all ingestion, SLA logic and
aggregation live there so Phase 2 (charts) and Phase 3 (AI) can reuse them.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import analytics
import ui_theme
from sla_core import (
    ALL, IngestError, by_company, by_month, kpi, list_companies,
    list_months, load_standardised,
)

st.set_page_config(page_title="Standardised SLA Reporting", page_icon="📊", layout="wide")

# Usage instrumentation — same PostHog project as every other app (see kit/).
analytics.APP = "standardised-sla"
analytics.page_open()

ui_theme.inject_css()
st.markdown('<div class="app-title">Standardised SLA</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">Upload a Fresh SLA export, then filter by company and month.</div>',
            unsafe_allow_html=True)


@st.cache_data(show_spinner="Processing export…")
def _process(data: bytes, filename: str):
    res = load_standardised(data, filename)
    return res.df, res.row_count, res.warnings


# ── 1. Upload ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("1 · Upload")
    upload = st.file_uploader("Fresh SLA export", type=["csv", "xlsx", "xls"],
                              help="The ticket-level export downloaded from Fresh.")

if upload is None:
    st.info("⬅️ Upload a Fresh export (CSV or XLSX) to begin.")
    st.stop()

try:
    df, row_count, warnings = _process(upload.getvalue(), upload.name)
except IngestError as e:
    st.error(f"Could not process the file: {e}")
    st.stop()

for w in warnings:
    st.warning(w)

# ── 2. Filters ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("2 · Filter")
    company = st.selectbox("Company", [ALL] + list_companies(df))
    month = st.selectbox("Month", [ALL] + list_months(df))

st.success(f"Loaded **{row_count:,}** tickets.")

# Track each distinct export processed (once per file, not on every rerun/filter).
if st.session_state.get("_tracked_file") != upload.name:
    st.session_state["_tracked_file"] = upload.name
    analytics.track("export_processed", rows=row_count)

# ── 3. KPI output ────────────────────────────────────────────────────────────
result = kpi(df, company, month)

ui_theme.kpi_hero(result)
st.write("")

with st.expander("KPI output (JSON — the Phase 1 API contract)"):
    st.code(json.dumps(result, indent=2), language="json")

st.divider()

# ── Supporting breakdowns (mirror the existing manual reports) ────────────────
left, right = st.columns(2)

with left:
    scope = month if month != ALL else "all months"
    st.markdown(f'<div class="section-label">SLA by company · {scope}</div>',
                unsafe_allow_html=True)
    st.dataframe(by_company(df, month=None if month == ALL else month),
                 hide_index=True, use_container_width=True)

with right:
    label = "all companies" if company == ALL else company
    st.markdown(f'<div class="section-label">SLA by month · {label}</div>',
                unsafe_allow_html=True)
    trend = by_month(df, company=None if company == ALL else company)
    st.dataframe(trend, hide_index=True, use_container_width=True)
    if len(trend) > 1:
        st.line_chart(trend.set_index("Month")["% Within"], height=180)

# ── Ticket detail + export ───────────────────────────────────────────────────
from sla_core.aggregate import filter_frame  # noqa: E402

detail = filter_frame(df, company, month)
with st.expander(f"Ticket detail ({len(detail):,} rows)"):
    st.dataframe(detail, hide_index=True, use_container_width=True)
    st.download_button(
        "Download filtered tickets (CSV)",
        detail.to_csv(index=False).encode("utf-8"),
        file_name=f"sla_{result['company']}_{result['month']}.csv".replace(" ", "_"),
        mime="text/csv",
    )
