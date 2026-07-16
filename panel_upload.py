"""Upload & Report panel — the Phase 1 SLA reporting flow, as a render() function
so it can live inside a tab of the unified dashboard.
"""
from __future__ import annotations

import json

import streamlit as st

import analytics
import ui_theme
from sla_core import (
    ALL, IngestError, by_company, by_month, kpi, list_companies,
    list_months, load_standardised,
)
from sla_core.aggregate import filter_frame


@st.cache_data(show_spinner="Processing export…")
def _process(data: bytes, filename: str):
    res = load_standardised(data, filename)
    return res.df, res.row_count, res.warnings


def render() -> None:
    st.markdown('<div class="section-label">Upload a Fresh SLA export</div>',
                unsafe_allow_html=True)
    upload = st.file_uploader("Fresh SLA export", type=["csv", "xlsx", "xls"],
                              label_visibility="collapsed",
                              help="The ticket-level export downloaded from Fresh.")
    if upload is None:
        st.info("Upload a Fresh export (CSV or XLSX) to see SLA results.")
        return

    try:
        df, row_count, warnings = _process(upload.getvalue(), upload.name)
    except IngestError as e:
        st.error(f"Could not process the file: {e}")
        return

    for w in warnings:
        st.warning(w)

    # Track each distinct export processed (once per file, not on every rerun).
    if st.session_state.get("_tracked_file") != upload.name:
        st.session_state["_tracked_file"] = upload.name
        analytics.track("export_processed", rows=row_count)

    col_c, col_m = st.columns(2)
    with col_c:
        company = st.selectbox("Company", [ALL] + list_companies(df))
    with col_m:
        month = st.selectbox("Month", [ALL] + list_months(df))

    st.caption(f"Loaded {row_count:,} tickets.")

    result = kpi(df, company, month)
    ui_theme.kpi_hero(result)
    st.write("")

    with st.expander("KPI output (JSON — the Phase 1 API contract)"):
        st.code(json.dumps(result, indent=2), language="json")

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

    detail = filter_frame(df, company, month)
    with st.expander(f"Ticket detail ({len(detail):,} rows)"):
        st.dataframe(detail, hide_index=True, use_container_width=True)
        st.download_button(
            "Download filtered tickets (CSV)",
            detail.to_csv(index=False).encode("utf-8"),
            file_name=f"sla_{result['company']}_{result['month']}.csv".replace(" ", "_"),
            mime="text/csv",
        )
