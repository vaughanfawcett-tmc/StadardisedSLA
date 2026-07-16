"""Standardised SLA — unified app.

One dashboard, two tabs:
  • 📊 Analytics — apps at a glance (uptime + usage across every app)
  • 📥 Upload & Report — turn a Fresh SLA export into KPIs

Thin entry over the panel modules; all logic lives in sla_core / panel_*.
"""
from __future__ import annotations

import streamlit as st

import analytics
import panel_metrics
import panel_upload
import ui_theme

st.set_page_config(page_title="Standardised SLA", page_icon="📊", layout="wide")

# Usage instrumentation — same PostHog project as every other app.
analytics.APP = "standardised-sla"
analytics.page_open()

ui_theme.inject_css()
st.markdown('<div class="app-title">Standardised SLA</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">Adoption &amp; uptime across every app · SLA reporting in one place.</div>',
            unsafe_allow_html=True)

tab_analytics, tab_upload = st.tabs(["📊  Analytics", "📥  Upload & Report"])

with tab_analytics:
    panel_metrics.render()

with tab_upload:
    panel_upload.render()
