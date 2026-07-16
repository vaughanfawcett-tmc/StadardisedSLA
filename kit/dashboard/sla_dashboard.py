"""
Standardised SLA — unified dashboard.

One custom UI over BOTH telemetry layers:
  • Uptime / SLA  -> Better Stack Uptime API   (data already flowing)
  • Usage         -> PostHog query API (HogQL)  (fills in once apps are instrumented)

Deploy as a 4th Streamlit-on-Render app. Configure via environment variables
(see .env.example / README.md). Degrades gracefully when a token or data is missing.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import altair as alt
import pandas as pd
import requests
import streamlit as st

# --------------------------------------------------------------------------- config
BS_TOKEN = os.environ.get("BETTERSTACK_API_TOKEN", "")
PH_KEY = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")
PH_PROJECT = os.environ.get("POSTHOG_PROJECT_ID", "225035")
PH_HOST = os.environ.get("POSTHOG_HOST", "https://eu.posthog.com")

BS_BASE = "https://uptime.betterstack.com/api/v2"

# palette — status colours are RESERVED (never reused for identity); TEAL is the accent
GOOD, WARN, CRIT, IDLE = "#2C8F63", "#B87A08", "#C7473C", "#7A8A88"
ACCENT = "#0C8A87"
# fixed categorical order for apps (assigned by identity, never cycled)
APP_HUES = ["#0C8A87", "#C77D11", "#5B6CC9", "#B0559B", "#4E8F3A"]

st.set_page_config(page_title="Standardised SLA", page_icon="📡", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1200px;}
      .stApp {background: #0C1413;}
      h1, h2, h3, p, span, div {color: #E7EEED;}
      .eyebrow {font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px;
        letter-spacing: .14em; text-transform: uppercase; color: #5AD0C8;}
      .tile {background:#101B1A; border:1px solid #213330; border-radius:14px; padding:16px 18px;}
      .tile .name {font-weight:600; font-size:15px;}
      .tile .big {font-size:30px; font-weight:680; font-variant-numeric: tabular-nums; margin-top:6px;}
      .tile .sub {font-family: ui-monospace, Menlo, monospace; font-size:12px; color:#8AA09E; margin-top:4px;}
      .pill {display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600;
        padding:3px 10px; border-radius:999px;}
      .dot {width:8px; height:8px; border-radius:50%; display:inline-block;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- Better Stack
@st.cache_data(ttl=180)
def bs_monitors() -> list[dict]:
    r = requests.get(f"{BS_BASE}/monitors", headers={"Authorization": f"Bearer {BS_TOKEN}"}, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


@st.cache_data(ttl=180)
def bs_sla(monitor_id: str, days: int) -> dict:
    frm = (date.today() - timedelta(days=days)).isoformat()
    to = date.today().isoformat()
    r = requests.get(
        f"{BS_BASE}/monitors/{monitor_id}/sla",
        headers={"Authorization": f"Bearer {BS_TOKEN}"},
        params={"from": frm, "to": to},
        timeout=20,
    )
    if r.status_code != 200:
        return {}
    return r.json().get("data", {}).get("attributes", {})


def status_pill(status: str) -> str:
    s = (status or "").lower()
    colour, label = {
        "up": (GOOD, "Up"),
        "down": (CRIT, "Down"),
        "paused": (IDLE, "Paused"),
        "pending": (WARN, "Pending"),
        "validating": (WARN, "Validating"),
        "maintenance": (IDLE, "Maintenance"),
    }.get(s, (IDLE, status or "—"))
    return (
        f'<span class="pill" style="background:{colour}22; color:{colour};">'
        f'<span class="dot" style="background:{colour};"></span>{label}</span>'
    )


# --------------------------------------------------------------------------- PostHog
@st.cache_data(ttl=180)
def ph_query(hogql: str) -> pd.DataFrame:
    r = requests.post(
        f"{PH_HOST}/api/projects/{PH_PROJECT}/query/",
        headers={"Authorization": f"Bearer {PH_KEY}", "Content-Type": "application/json"},
        json={"query": {"kind": "HogQLQuery", "query": hogql}},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    return pd.DataFrame(payload.get("results", []), columns=payload.get("columns", []))


def usage_totals(days: int) -> pd.DataFrame:
    return ph_query(
        f"""
        SELECT properties.app AS app,
               count() AS events,
               count(DISTINCT person_id) AS users
        FROM events
        WHERE timestamp > now() - INTERVAL {days} DAY
          AND properties.app IS NOT NULL
        GROUP BY app
        ORDER BY events DESC
        """
    )


def usage_trend(days: int) -> pd.DataFrame:
    return ph_query(
        f"""
        SELECT toDate(timestamp) AS day,
               properties.app AS app,
               count() AS events
        FROM events
        WHERE timestamp > now() - INTERVAL {days} DAY
          AND properties.app IS NOT NULL
        GROUP BY day, app
        ORDER BY day
        """
    )


# --------------------------------------------------------------------------- header + controls
st.markdown('<div class="eyebrow">Standardised SLA</div>', unsafe_allow_html=True)
st.markdown("# Apps at a glance")
st.caption("Uptime from Better Stack · usage from PostHog · unified in one view.")

days = st.sidebar.selectbox("Window", [7, 30, 90], index=1, format_func=lambda d: f"Last {d} days")
st.sidebar.caption("Data cached for 3 minutes. Reload to refresh.")

# --------------------------------------------------------------------------- SLA section
st.markdown("## Uptime & SLA")

if not BS_TOKEN:
    st.info(
        "Add **BETTERSTACK_API_TOKEN** to show live uptime. "
        "Get it at Better Stack → Settings → API tokens.",
        icon="🔑",
    )
else:
    try:
        monitors = bs_monitors()
    except Exception as exc:  # noqa: BLE001
        monitors = []
        st.error(f"Couldn't reach Better Stack: {exc}")

    monitors = [m for m in monitors if "onrender.com" in m.get("attributes", {}).get("url", "")]
    cols = st.columns(max(len(monitors), 1))
    for col, m in zip(cols, monitors):
        attrs = m["attributes"]
        sla = bs_sla(m["id"], days)
        avail = sla.get("availability")
        avail_txt = f"{avail:.2f}%" if isinstance(avail, (int, float)) else "—"
        incidents = sla.get("number_of_incidents", "—")
        name = attrs.get("pronounceable_name", attrs.get("url", "monitor")).replace(" — prod", "")
        with col:
            st.markdown(
                f"""
                <div class="tile">
                  <div class="name">{name}</div>
                  <div class="big">{avail_txt}</div>
                  <div class="sub">uptime · last {days}d</div>
                  <div style="margin-top:10px;">{status_pill(attrs.get('status'))}</div>
                  <div class="sub">{incidents} incident(s)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# --------------------------------------------------------------------------- Usage section
st.markdown("## Usage")

if not PH_KEY:
    st.info(
        "Add **POSTHOG_PERSONAL_API_KEY** to show usage. "
        "Get it at PostHog → Settings → Personal API keys (needs query:read scope).",
        icon="🔑",
    )
else:
    try:
        totals = usage_totals(days)
    except Exception as exc:  # noqa: BLE001
        totals = pd.DataFrame()
        st.error(f"Couldn't reach PostHog: {exc}")

    if totals.empty:
        st.warning(
            "No usage events yet. Instrument the apps (drop in `analytics.py`, set "
            "`analytics.APP`, redeploy) and events will appear here.",
            icon="⏳",
        )
    else:
        cols = st.columns(len(totals))
        for col, hue, (_, row) in zip(cols, APP_HUES, totals.iterrows()):
            with col:
                st.markdown(
                    f"""
                    <div class="tile">
                      <div class="name"><span class="dot" style="background:{hue};"></span>
                        &nbsp;{row['app']}</div>
                      <div class="big">{int(row['users']):,}</div>
                      <div class="sub">active users · last {days}d</div>
                      <div class="sub">{int(row['events']):,} events</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        trend = usage_trend(days)
        if not trend.empty:
            trend["day"] = pd.to_datetime(trend["day"])
            domain = list(totals["app"])
            chart = (
                alt.Chart(trend)
                .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=28))
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("events:Q", title="events / day"),
                    color=alt.Color(
                        "app:N",
                        scale=alt.Scale(domain=domain, range=APP_HUES[: len(domain)]),
                        legend=alt.Legend(title=None, orient="top"),
                    ),
                    tooltip=["day:T", "app:N", "events:Q"],
                )
                .properties(height=300)
                .configure_view(strokeOpacity=0)
                .configure_axis(grid=False, labelColor="#8AA09E", titleColor="#8AA09E")
            )
            st.altair_chart(chart, use_container_width=True)

st.divider()
st.caption("Add an app: register it in apps.json, add its Better Stack monitor, instrument it — it appears here automatically.")
