"""Analytics panel — apps at a glance.

Overview KPIs → uptime tiles (with health bars) → usage tiles → an events
trend chart. Apple light theme; categorical palette validated for CVD.
Self-contained (reads config from env), degrades gracefully.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import altair as alt
import pandas as pd
import requests
import streamlit as st

import ui_theme

BS_TOKEN = os.environ.get("BETTERSTACK_API_TOKEN", "")
PH_KEY = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")
PH_PROJECT = os.environ.get("POSTHOG_PROJECT_ID", "225035")
PH_HOST = os.environ.get("POSTHOG_HOST", "https://eu.posthog.com")
BS_BASE = "https://uptime.betterstack.com/api/v2"

# Categorical hues, validated for the DARK surface (worst adjacent CVD ΔE 28.2).
# Assigned by identity, fixed order.
APP_HUES = ["#0A84FF", "#C06E00", "#0E9DBC", "#BF5AF2", "#1F9C3C"]


def _hue(name: str, order: list[str]) -> str:
    try:
        return APP_HUES[order.index(name) % len(APP_HUES)]
    except ValueError:
        return ui_theme.SUBTLE


# ── data ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def _bs_monitors() -> list[dict]:
    r = requests.get(f"{BS_BASE}/monitors",
                     headers={"Authorization": f"Bearer {BS_TOKEN}"}, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


@st.cache_data(ttl=180)
def _bs_sla(monitor_id: str, days: int) -> dict:
    frm = (date.today() - timedelta(days=days)).isoformat()
    r = requests.get(f"{BS_BASE}/monitors/{monitor_id}/sla",
                     headers={"Authorization": f"Bearer {BS_TOKEN}"},
                     params={"from": frm, "to": date.today().isoformat()}, timeout=20)
    return r.json().get("data", {}).get("attributes", {}) if r.status_code == 200 else {}


@st.cache_data(ttl=180)
def _ph(hogql: str) -> pd.DataFrame:
    r = requests.post(f"{PH_HOST}/api/projects/{PH_PROJECT}/query/",
                      headers={"Authorization": f"Bearer {PH_KEY}",
                               "Content-Type": "application/json"},
                      json={"query": {"kind": "HogQLQuery", "query": hogql}}, timeout=30)
    r.raise_for_status()
    p = r.json()
    return pd.DataFrame(p.get("results", []), columns=p.get("columns", []))


def _usage_totals(days: int) -> pd.DataFrame:
    return _ph(f"""SELECT properties.app AS app, count() AS events,
                          count(DISTINCT person_id) AS users
                   FROM events WHERE timestamp > now() - INTERVAL {days} DAY
                     AND properties.app IS NOT NULL GROUP BY app ORDER BY events DESC""")


def _usage_trend(days: int) -> pd.DataFrame:
    return _ph(f"""SELECT toDate(timestamp) AS day, properties.app AS app, count() AS events
                   FROM events WHERE timestamp > now() - INTERVAL {days} DAY
                     AND properties.app IS NOT NULL GROUP BY day, app ORDER BY day""")


# ── render helpers ───────────────────────────────────────────────────────────
def _kpi(label: str, value: str, foot: str, accent: str) -> str:
    return f"""<div class="kpi" style="--accent:{accent};">
      <div class="k-label">{label}</div><div class="k-value">{value}</div>
      <div class="k-foot">{foot}</div></div>"""


def _mtile(name: str, big: str, sub: str, dot: str, bar_pct: float, bar_color: str,
           foot: str) -> str:
    return f"""<div class="mtile">
      <div class="m-name"><span class="dot" style="background:{dot}"></span>{name}</div>
      <div class="m-big">{big}</div><div class="m-sub">{sub}</div>
      <div class="m-bar"><span style="width:{max(2,min(bar_pct,100)):.1f}%;background:{bar_color}"></span></div>
      <div class="m-sub" style="margin-top:8px">{foot}</div></div>"""


def _trend_chart(trend: pd.DataFrame, order: list[str]):
    trend = trend.copy()
    trend["day"] = pd.to_datetime(trend["day"])
    domain = [a for a in order if a in set(trend["app"])]
    rng = [_hue(a, order) for a in domain]
    base = alt.Chart(trend).encode(
        x=alt.X("day:T", title=None, axis=alt.Axis(format="%b %d", labelColor=ui_theme.SUBTLE,
                                                   domainColor=ui_theme.HAIRLINE, tickColor=ui_theme.HAIRLINE, grid=False)),
        y=alt.Y("events:Q", title="events / day",
                axis=alt.Axis(labelColor=ui_theme.SUBTLE, titleColor=ui_theme.SUBTLE,
                              gridColor=ui_theme.HAIRLINE, gridOpacity=0.5, domainOpacity=0, tickOpacity=0)),
        color=alt.Color("app:N", scale=alt.Scale(domain=domain, range=rng),
                        legend=alt.Legend(title=None, orient="top", labelColor=ui_theme.INK)),
        tooltip=[alt.Tooltip("day:T", title="Day"), alt.Tooltip("app:N", title="App"),
                 alt.Tooltip("events:Q", title="Events")],
    )
    area = base.mark_area(opacity=0.14, interpolate="monotone")
    line = base.mark_line(strokeWidth=2.5, interpolate="monotone",
                          point=alt.OverlayMarkDef(size=48, filled=True))
    return (area + line).properties(height=280, background="transparent").configure_view(
        strokeOpacity=0).configure_axis(labelFont="-apple-system", titleFont="-apple-system")


# ── main ─────────────────────────────────────────────────────────────────────
def render() -> None:
    days = st.radio("Window", [7, 30, 90], index=1, horizontal=True,
                    format_func=lambda d: f"Last {d} days", key="metrics_window",
                    label_visibility="collapsed")

    # gather uptime
    monitors, avgs = [], []
    if BS_TOKEN:
        try:
            monitors = [m for m in _bs_monitors()
                        if "onrender.com" in m.get("attributes", {}).get("url", "")]
        except Exception:  # noqa: BLE001
            monitors = []
    mon_sla = {}
    for m in monitors:
        s = _bs_sla(m["id"], days)
        mon_sla[m["id"]] = s
        if isinstance(s.get("availability"), (int, float)):
            avgs.append(s["availability"])

    # gather usage
    totals = pd.DataFrame()
    if PH_KEY:
        try:
            totals = _usage_totals(days)
        except Exception:  # noqa: BLE001
            totals = pd.DataFrame()
    order = list(totals["app"]) if not totals.empty else []

    # ── overview strip ───────────────────────────────────────────────────────
    fleet_up = f"{sum(avgs) / len(avgs):.2f}%" if avgs else "—"
    up_now = sum(1 for m in monitors if (m["attributes"].get("status") or "").lower() == "up")
    users = int(totals["users"].sum()) if not totals.empty else 0
    events = int(totals["events"].sum()) if not totals.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi("Apps", str(len(monitors) or "—"), f"{up_now} up now", ui_theme.BLUE), unsafe_allow_html=True)
    k2.markdown(_kpi("Fleet uptime", fleet_up, f"last {days} days", ui_theme.GREEN), unsafe_allow_html=True)
    k3.markdown(_kpi("Active users", f"{users:,}", f"last {days} days", "#AF52DE"), unsafe_allow_html=True)
    k4.markdown(_kpi("Usage events", f"{events:,}", f"last {days} days", "#FF9500"), unsafe_allow_html=True)

    # ── uptime ───────────────────────────────────────────────────────────────
    st.markdown('<div class="eyebrow">Uptime &amp; SLA</div>', unsafe_allow_html=True)
    if not BS_TOKEN:
        st.info("Add BETTERSTACK_API_TOKEN to show live uptime.", icon="🔑")
    elif monitors:
        cols = st.columns(len(monitors))
        for col, m in zip(cols, monitors):
            a = m["attributes"]
            s = mon_sla.get(m["id"], {})
            avail = s.get("availability")
            pct = float(avail) if isinstance(avail, (int, float)) else 0.0
            avail_txt = f"{pct:.2f}%" if avail is not None else "—"
            name = a.get("pronounceable_name", a.get("url", "monitor")).replace(" — prod", "")
            up = (a.get("status") or "").lower() == "up"
            color = ui_theme.GREEN if up and pct >= 99 else (ui_theme.AMBER if pct >= 95 else ui_theme.RED)
            col.markdown(_mtile(name, avail_txt, f"uptime · last {days}d",
                                ui_theme.GREEN if up else ui_theme.RED, pct, color,
                                f"{s.get('number_of_incidents', 0)} incident(s)"),
                         unsafe_allow_html=True)

    # ── usage ────────────────────────────────────────────────────────────────
    st.markdown('<div class="eyebrow">Usage</div>', unsafe_allow_html=True)
    if not PH_KEY:
        st.info("Add POSTHOG_PERSONAL_API_KEY (scope query:read) to show usage.", icon="🔑")
        return
    if totals.empty:
        st.info("No usage events yet — they'll appear here as people use the apps.", icon="⏳")
        return

    cols = st.columns(max(len(totals), 1))
    peak = max(int(totals["events"].max()), 1)
    for col, (_, row) in zip(cols, totals.iterrows()):
        hue = _hue(str(row["app"]), order)
        col.markdown(_mtile(str(row["app"]), f"{int(row['users']):,}", f"active users · last {days}d",
                            hue, 100 * int(row["events"]) / peak, hue,
                            f"{int(row['events']):,} events"), unsafe_allow_html=True)

    # events trend
    try:
        trend = _usage_trend(days)
    except Exception:  # noqa: BLE001
        trend = pd.DataFrame()
    if not trend.empty:
        st.markdown('<div class="eyebrow">Events over time</div>', unsafe_allow_html=True)
        st.altair_chart(_trend_chart(trend, order), use_container_width=True)
