"""Upload & Report panel — the Phase 1 SLA reporting flow, as a render() function
so it can live inside a tab of the unified dashboard.
"""
from __future__ import annotations

import json

import altair as alt
import streamlit as st

import analytics
import ui_theme
from sla_core import (
    ALL, COMBINED, METRICS, IngestError, by_company, by_month, kpi,
    list_companies, list_months, load_standardised,
)
from sla_core import history
from sla_core.aggregate import filter_frame, metric_scope


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

    # Track each distinct export processed (once per file, not on every rerun),
    # and record it in the persistent report history (deduped by file hash).
    if st.session_state.get("_tracked_file") != upload.name:
        st.session_state["_tracked_file"] = upload.name
        analytics.track("export_processed", rows=row_count)
    try:
        _, newly_saved = history.record_upload(upload.getvalue(), upload.name, df)
    except Exception:  # noqa: BLE001 — history must never break reporting
        newly_saved = False

    col_r, col_c, col_m = st.columns(3)
    with col_r:
        metric = st.selectbox("Report", list(METRICS))
    with col_c:
        company = st.selectbox("Company", [ALL] + list_companies(df))
    with col_m:
        month = st.selectbox("Month", [ALL] + list_months(df))

    caption = f"Loaded {row_count:,} tickets."
    if newly_saved:
        caption += " Saved to report history."
    if metric != COMBINED:
        in_scope = len(metric_scope(df, metric)[0])
        caption += (f" {in_scope:,} carry a {metric.lower()} SLA target; "
                    "the report covers those.")
    st.caption(caption)

    result = kpi(df, company, month, metric)
    ui_theme.kpi_hero(result)
    st.write("")

    with st.expander("KPI output (JSON — the Phase 1 API contract)"):
        st.code(json.dumps(result, indent=2), language="json")

    left, right = st.columns(2)
    with left:
        scope = month if month != ALL else "all months"
        st.markdown(f'<div class="section-label">SLA by company · {scope}</div>',
                    unsafe_allow_html=True)
        st.dataframe(by_company(df, month=None if month == ALL else month, metric=metric),
                     hide_index=True, use_container_width=True)
    with right:
        label = "all companies" if company == ALL else company
        st.markdown(f'<div class="section-label">SLA by month · {label}</div>',
                    unsafe_allow_html=True)
        trend = by_month(df, company=None if company == ALL else company, metric=metric)
        st.dataframe(trend, hide_index=True, use_container_width=True)
        if len(trend) > 1:
            tdf = trend[["Month", "% Within"]].rename(columns={"% Within": "pct"}).copy()
            tdf["pct"] = tdf["pct"].astype(float)
            lo = max(0.0, tdf["pct"].min() - 5)
            # Single mark + explicit domain: an area layer alongside a scale
            # domain collapses the plot in current Streamlit/vega-lite.
            chart = alt.Chart(tdf).mark_line(
                strokeWidth=2.5, interpolate="monotone", color=ui_theme.BLUE,
                point=alt.OverlayMarkDef(size=48, filled=True, color=ui_theme.BLUE),
            ).encode(
                x=alt.X("Month:N", title=None,
                        axis=alt.Axis(labelAngle=0, labelColor=ui_theme.SUBTLE,
                                      domainColor=ui_theme.HAIRLINE, tickColor=ui_theme.HAIRLINE)),
                y=alt.Y("pct:Q", title="% within SLA",
                        scale=alt.Scale(domain=[lo, 100]),
                        axis=alt.Axis(labelColor=ui_theme.SUBTLE, titleColor=ui_theme.SUBTLE,
                                      gridColor=ui_theme.HAIRLINE, gridOpacity=0.5,
                                      domainOpacity=0, tickOpacity=0)),
                tooltip=[alt.Tooltip("Month:N"), alt.Tooltip("pct:Q", title="% within", format=".1f")],
            )
            st.altair_chart(chart.properties(height=200, background="transparent")
                            .configure_view(strokeOpacity=0), use_container_width=True)

    detail = filter_frame(df, company, month)
    with st.expander(f"Ticket detail ({len(detail):,} rows)"):
        st.dataframe(detail, hide_index=True, use_container_width=True)
        st.download_button(
            "Download filtered tickets (CSV)",
            detail.to_csv(index=False).encode("utf-8"),
            file_name=f"sla_{result['company']}_{result['month']}.csv".replace(" ", "_"),
            mime="text/csv",
        )
