"""Analytics panel — apps at a glance (uptime from Better Stack + usage from
PostHog), rendered in the Apple light theme so it matches the Upload panel.

Self-contained: reads its config from env, degrades gracefully when a token or
data is missing. Exposed as render() so it can live in a tab.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

import ui_theme

BS_TOKEN = os.environ.get("BETTERSTACK_API_TOKEN", "")
PH_KEY = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")
PH_PROJECT = os.environ.get("POSTHOG_PROJECT_ID", "225035")
PH_HOST = os.environ.get("POSTHOG_HOST", "https://eu.posthog.com")
BS_BASE = "https://uptime.betterstack.com/api/v2"


# ── Better Stack ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def _bs_monitors() -> list[dict]:
    r = requests.get(f"{BS_BASE}/monitors",
                     headers={"Authorization": f"Bearer {BS_TOKEN}"}, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


@st.cache_data(ttl=180)
def _bs_sla(monitor_id: str, days: int) -> dict:
    frm = (date.today() - timedelta(days=days)).isoformat()
    to = date.today().isoformat()
    r = requests.get(f"{BS_BASE}/monitors/{monitor_id}/sla",
                     headers={"Authorization": f"Bearer {BS_TOKEN}"},
                     params={"from": frm, "to": to}, timeout=20)
    if r.status_code != 200:
        return {}
    return r.json().get("data", {}).get("attributes", {})


# ── PostHog ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def _ph_query(hogql: str) -> pd.DataFrame:
    r = requests.post(f"{PH_HOST}/api/projects/{PH_PROJECT}/query/",
                      headers={"Authorization": f"Bearer {PH_KEY}",
                               "Content-Type": "application/json"},
                      json={"query": {"kind": "HogQLQuery", "query": hogql}}, timeout=30)
    r.raise_for_status()
    p = r.json()
    return pd.DataFrame(p.get("results", []), columns=p.get("columns", []))


def _usage_totals(days: int) -> pd.DataFrame:
    return _ph_query(
        f"""SELECT properties.app AS app, count() AS events,
                   count(DISTINCT person_id) AS users
            FROM events
            WHERE timestamp > now() - INTERVAL {days} DAY AND properties.app IS NOT NULL
            GROUP BY app ORDER BY events DESC""")


def _tile(name: str, big: str, sub: str, dot: str | None = None, foot: str = "") -> str:
    dothtml = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{dot};margin-right:7px;"></span>' if dot else ""
    foothtml = f'<div style="color:{ui_theme.SUBTLE};font-size:.8rem;margin-top:6px;">{foot}</div>' if foot else ""
    return f"""<div class="card" style="padding:18px 20px;">
      <div style="font-weight:600;color:{ui_theme.INK};">{dothtml}{name}</div>
      <div style="font-size:1.9rem;font-weight:600;color:{ui_theme.INK};letter-spacing:-.02em;
                  font-variant-numeric:tabular-nums;margin-top:6px;">{big}</div>
      <div style="color:{ui_theme.SUBTLE};font-size:.82rem;margin-top:2px;">{sub}</div>
      {foothtml}
    </div>"""


def render() -> None:
    days = st.radio("Window", [7, 30, 90], index=1, horizontal=True,
                    format_func=lambda d: f"Last {d} days", key="metrics_window")

    # ── Uptime ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Uptime &amp; SLA</div>', unsafe_allow_html=True)
    if not BS_TOKEN:
        st.info("Add BETTERSTACK_API_TOKEN to show live uptime.", icon="🔑")
    else:
        try:
            monitors = [m for m in _bs_monitors()
                        if "onrender.com" in m.get("attributes", {}).get("url", "")]
        except Exception as exc:  # noqa: BLE001
            monitors = []
            st.error(f"Couldn't reach Better Stack: {exc}")
        if monitors:
            cols = st.columns(len(monitors))
            for col, m in zip(cols, monitors):
                a = m["attributes"]
                sla = _bs_sla(m["id"], days)
                avail = sla.get("availability")
                avail_txt = f"{avail:.2f}%" if isinstance(avail, (int, float)) else "—"
                name = a.get("pronounceable_name", a.get("url", "monitor")).replace(" — prod", "")
                up = (a.get("status") or "").lower() == "up"
                dot = ui_theme.GREEN if up else ui_theme.RED
                col.markdown(_tile(name, avail_txt, f"uptime · last {days}d", dot,
                                   f"{sla.get('number_of_incidents', 0)} incident(s)"),
                             unsafe_allow_html=True)

    st.write("")
    # ── Usage ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Usage</div>', unsafe_allow_html=True)
    if not PH_KEY:
        st.info("Add POSTHOG_PERSONAL_API_KEY (scope query:read) to show usage.", icon="🔑")
        return
    try:
        totals = _usage_totals(days)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't reach PostHog: {exc}")
        return
    if totals.empty:
        st.info("No usage events yet — they'll appear here as people use the apps.", icon="⏳")
        return
    cols = st.columns(len(totals))
    for col, (_, row) in zip(cols, totals.iterrows()):
        col.markdown(_tile(str(row["app"]), f"{int(row['users']):,}",
                           f"active users · last {days}d", ui_theme.GREEN,
                           f"{int(row['events']):,} events"), unsafe_allow_html=True)
