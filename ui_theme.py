"""Apple-style visual layer for the Streamlit app.

Kept separate from app logic: injects a global stylesheet and renders the KPI
hero (an Apple Fitness-style activity ring for the SLA %). Pure presentation —
no data logic lives here.
"""
from __future__ import annotations

import streamlit as st

# ── Apple system palette ──────────────────────────────────────────────────────
INK = "#1D1D1F"        # primary text (near-black)
SUBTLE = "#6E6E73"     # secondary text
CANVAS = "#F5F5F7"     # page background
CARD = "#FFFFFF"
HAIRLINE = "#D2D2D7"
BLUE = "#0071E3"       # Apple blue accent
GREEN = "#34C759"      # SF system green
AMBER = "#FF9F0A"
RED = "#FF3B30"

FONT = ('-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
        '"Helvetica Neue", Helvetica, Arial, sans-serif')


def health_color(pct: float) -> str:
    """SLA health -> Apple system colour."""
    if pct >= 98:
        return GREEN
    if pct >= 95:
        return AMBER
    return RED


def stylesheet() -> str:
    return f"""
        <style>
          @import url('https://rsms.me/inter/inter.css');
          html, body, [class*="css"] {{ font-family: {FONT}; }}
          .stApp {{ background: {CANVAS}; }}
          #MainMenu, header[data-testid="stHeader"], footer {{ visibility: hidden; }}
          .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1120px; }}

          /* Sidebar: frosted, hairline edge */
          section[data-testid="stSidebar"] {{
            background: rgba(255,255,255,0.72);
            backdrop-filter: saturate(180%) blur(20px);
            border-right: 1px solid {HAIRLINE};
          }}

          /* Headings */
          h1, h2, h3 {{ color: {INK}; letter-spacing: -0.02em; font-weight: 600; }}
          .app-title {{ font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em;
                        color: {INK}; margin: 0 0 .1rem 0; }}
          .app-sub {{ color: {SUBTLE}; font-size: 1.02rem; margin-bottom: 1.6rem; }}

          /* Generic card */
          .card {{ background: {CARD}; border-radius: 20px; padding: 26px 28px;
                   box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 10px 30px rgba(0,0,0,.05);
                   border: 1px solid rgba(0,0,0,.03); }}

          /* KPI hero */
          .hero {{ display: flex; align-items: center; gap: 40px; flex-wrap: wrap; }}
          .hero .context {{ color: {SUBTLE}; font-size: .82rem; font-weight: 600;
                            text-transform: uppercase; letter-spacing: .08em; margin-bottom: 14px; }}
          .stats {{ display: flex; gap: 40px; flex-wrap: wrap; }}
          .stat .num {{ font-size: 2.1rem; font-weight: 600; color: {INK}; letter-spacing: -0.02em;
                        line-height: 1; font-variant-numeric: tabular-nums; }}
          .stat .lbl {{ color: {SUBTLE}; font-size: .9rem; margin-top: 6px; }}
          .stat .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%;
                        margin-right:7px; vertical-align: middle; }}

          /* Streamlit dataframe: soften into a card */
          [data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden;
                                         border: 1px solid {HAIRLINE}; }}

          /* Buttons */
          .stDownloadButton button, .stButton button {{
            border-radius: 980px; border: 1px solid {HAIRLINE};
            background: {CARD}; color: {BLUE}; font-weight: 600; padding: .5rem 1.1rem; }}
          .stDownloadButton button:hover, .stButton button:hover {{ border-color: {BLUE}; }}

          .section-label {{ color: {INK}; font-weight: 600; font-size: 1.05rem;
                            letter-spacing: -0.01em; margin: 6px 0 10px; }}
        </style>
        """


def inject_css() -> None:
    st.markdown(stylesheet(), unsafe_allow_html=True)


def _ring_svg(pct: float, color: str) -> str:
    r, sw = 78, 14
    import math
    c = 2 * math.pi * r
    dash = c * max(0.0, min(pct, 100.0)) / 100.0
    return f"""
    <svg width="196" height="196" viewBox="0 0 196 196">
      <circle cx="98" cy="98" r="{r}" fill="none" stroke="#E9E9EB" stroke-width="{sw}"/>
      <circle cx="98" cy="98" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}"
              stroke-linecap="round" stroke-dasharray="{dash:.2f} {c:.2f}"
              transform="rotate(-90 98 98)"/>
      <text x="98" y="94" text-anchor="middle" font-size="42" font-weight="600"
            fill="{INK}" style="font-family:{FONT};letter-spacing:-1px">{pct:.1f}<tspan font-size="20" dy="-14">%</tspan></text>
      <text x="98" y="122" text-anchor="middle" font-size="13" fill="{SUBTLE}"
            style="font-family:{FONT};letter-spacing:.5px">WITHIN SLA</text>
    </svg>
    """


def kpi_hero_html(result: dict) -> str:
    """Build the primary-KPI activity-ring hero card as an HTML string."""
    pct = float(result["sla_percentage"])
    color = health_color(pct)
    ctx = f"{result['company']} · {result['month']}"
    return f"""
        <div class="card hero">
          <div>{_ring_svg(pct, color)}</div>
          <div style="flex:1; min-width:260px;">
            <div class="context">{ctx}</div>
            <div class="stats">
              <div class="stat"><div class="num">{result['total_tickets']:,}</div>
                   <div class="lbl">Total tickets</div></div>
              <div class="stat"><div class="num"><span class="dot" style="background:{GREEN}"></span>{result['within_sla']:,}</div>
                   <div class="lbl">Within SLA</div></div>
              <div class="stat"><div class="num"><span class="dot" style="background:{RED if result['outside_sla'] else HAIRLINE}"></span>{result['outside_sla']:,}</div>
                   <div class="lbl">Outside SLA</div></div>
            </div>
          </div>
        </div>
        """


def kpi_hero(result: dict) -> None:
    st.markdown(kpi_hero_html(result), unsafe_allow_html=True)
