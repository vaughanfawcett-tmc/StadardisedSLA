"""History panel — every processed upload, remembered.

Reads the persistent snapshot store (sla_core.history): cross-upload SLA
trend, all-time KPIs, and the upload log. Re-uploads of the same file are
deduped; a re-export covering the same month supersedes the older snapshot.
"""
from __future__ import annotations

import altair as alt
import streamlit as st

import ui_theme
from sla_core import ALL, METRICS
from sla_core import history


def _kpi(label: str, value: str, foot: str, accent: str) -> str:
    return f"""<div class="kpi" style="--accent:{accent};">
      <div class="k-label">{label}</div><div class="k-value">{value}</div>
      <div class="k-foot">{foot}</div></div>"""


def _trend_chart(t) -> alt.Chart:
    tdf = t[["Month", "% Within"]].rename(columns={"% Within": "pct"}).copy()
    tdf["pct"] = tdf["pct"].astype(float)
    lo = max(0.0, tdf["pct"].min() - 5)
    # Single mark + explicit domain: an area layer alongside a scale domain
    # collapses the plot in current Streamlit/vega-lite.
    return alt.Chart(tdf).mark_line(
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
    ).properties(height=220, background="transparent").configure_view(strokeOpacity=0)


def render() -> None:
    try:
        ups = history.uploads()
    except Exception:  # noqa: BLE001 — a broken/missing DB shows as empty history
        ups = None
    if ups is None or ups.empty:
        st.info("No reports recorded yet. Process an export in **Upload & Report** "
                "and it will appear here automatically.", icon="🕘")
        return

    col_r, col_c = st.columns(2)
    with col_r:
        metric = st.selectbox("Report", list(METRICS), key="history_metric")
    with col_c:
        company = st.selectbox("Company", [ALL] + history.companies(),
                               key="history_company")

    o = history.overall(metric, company)
    pct = o["sla_percentage"]
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi("Reports on file", str(len(ups)),
                     f"{o['months']} month(s) covered", ui_theme.BLUE),
                unsafe_allow_html=True)
    k2.markdown(_kpi("All-time SLA", f"{pct:.1f}%" if o["total_tickets"] else "—",
                     metric.lower(), ui_theme.health_color(pct)), unsafe_allow_html=True)
    k3.markdown(_kpi("Tickets recorded", f"{o['total_tickets']:,}",
                     "latest snapshot per month", "#AF52DE"), unsafe_allow_html=True)
    k4.markdown(_kpi("Outside SLA", f"{o['outside_sla']:,}", "all time", "#FF9500"),
                unsafe_allow_html=True)

    t = history.trend(metric, company)
    if len(t) > 1:
        st.markdown('<div class="eyebrow">SLA trend across all uploads</div>',
                    unsafe_allow_html=True)
        st.altair_chart(_trend_chart(t), use_container_width=True)
    if not t.empty:
        st.markdown('<div class="eyebrow">Month by month</div>', unsafe_allow_html=True)
        st.dataframe(t, hide_index=True, use_container_width=True)

    st.markdown('<div class="eyebrow">Upload log</div>', unsafe_allow_html=True)
    st.dataframe(ups, hide_index=True, use_container_width=True)
    with st.expander("Remove an upload from history"):
        pick = st.selectbox(
            "Upload", ups["ID"].tolist(),
            format_func=lambda i: (f"#{i} · "
                                   f"{ups.loc[ups['ID'] == i, 'File'].iloc[0]} · "
                                   f"{ups.loc[ups['ID'] == i, 'Uploaded'].iloc[0]}"),
            key="history_delete_pick")
        if st.button("Remove from history"):
            history.delete_upload(int(pick))
            st.rerun()
