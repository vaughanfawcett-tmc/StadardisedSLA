"""Dark command-center visual layer for the Standardised SLA app.

Injects a global stylesheet and renders the KPI hero (activity-ring SLA gauge).
Pure presentation — no data logic.
"""
from __future__ import annotations

import math

import streamlit as st

# ── Dark command-center palette ───────────────────────────────────────────────
INK = "#E8EDF3"        # primary text
SUBTLE = "#8B98A8"     # secondary text
CANVAS = "#0A0E13"     # page background (deep)
CARD = "#141A22"       # surface
CARD_HI = "#1A222C"    # raised surface
HAIRLINE = "#243142"
BLUE = "#0A84FF"       # accent
GREEN = "#32D74B"      # status good
AMBER = "#FF9F0A"      # status warn
RED = "#FF453A"        # status critical

FONT = ('-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
        '"Helvetica Neue", Helvetica, Arial, sans-serif')


def health_color(pct: float) -> str:
    if pct >= 98:
        return GREEN
    if pct >= 95:
        return AMBER
    return RED


def stylesheet() -> str:
    return f"""
        <style>
          html, body, [class*="css"] {{ font-family: {FONT}; }}
          .stApp {{
            background:
              radial-gradient(1100px 500px at 78% -8%, rgba(10,132,255,.10), transparent 60%),
              radial-gradient(900px 500px at 5% 0%, rgba(191,90,242,.06), transparent 55%),
              {CANVAS};
            color: {INK};
          }}
          #MainMenu, header[data-testid="stHeader"], footer {{ visibility: hidden; }}
          .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }}

          section[data-testid="stSidebar"] {{
            background: rgba(14,19,26,0.7);
            backdrop-filter: saturate(160%) blur(20px);
            border-right: 1px solid {HAIRLINE};
          }}

          h1, h2, h3 {{ color: {INK}; letter-spacing: -0.02em; font-weight: 600; }}
          .app-title {{ font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em;
                        color: {INK}; margin: 0 0 .1rem 0; }}
          .app-sub {{ color: {SUBTLE}; font-size: 1.02rem; margin-bottom: 1.4rem; }}
          p, span, label, .stMarkdown {{ color: {INK}; }}

          .eyebrow {{ color: {SUBTLE}; font-size: .72rem; font-weight: 700;
                      text-transform: uppercase; letter-spacing: .12em; margin: 28px 0 12px; }}
          .section-label {{ color: {INK}; font-weight: 600; font-size: 1.05rem;
                            letter-spacing: -0.01em; margin: 6px 0 10px; }}

          .card {{ background: {CARD}; border-radius: 20px; padding: 24px 26px;
                   box-shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 18px 44px rgba(0,0,0,.5);
                   border: 1px solid {HAIRLINE}; }}

          /* KPI overview strip */
          .kpi {{ background: {CARD}; border-radius: 18px; padding: 18px 20px;
                  border: 1px solid {HAIRLINE}; position: relative; overflow: hidden;
                  box-shadow: 0 14px 34px rgba(0,0,0,.45); }}
          .kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
                          background: var(--accent, {BLUE});
                          box-shadow: 0 0 16px 1px var(--accent, {BLUE}); }}
          .kpi .k-label {{ color: {SUBTLE}; font-size: .72rem; font-weight: 700;
                           text-transform: uppercase; letter-spacing: .08em; }}
          .kpi .k-value {{ color: {INK}; font-size: 2rem; font-weight: 650; letter-spacing: -.02em;
                           font-variant-numeric: tabular-nums; line-height: 1.05; margin-top: 8px; }}
          .kpi .k-foot {{ color: {SUBTLE}; font-size: .8rem; margin-top: 4px; }}

          /* metric tile with health bar */
          .mtile {{ background: {CARD}; border-radius: 18px; padding: 18px 20px;
                    border: 1px solid {HAIRLINE}; box-shadow: 0 14px 34px rgba(0,0,0,.45); }}
          .mtile .m-name {{ font-weight: 600; color: {INK}; font-size: .95rem; display:flex;
                            align-items:center; gap:8px; }}
          .mtile .m-big {{ font-size: 1.85rem; font-weight: 650; color: {INK}; letter-spacing:-.02em;
                           font-variant-numeric: tabular-nums; margin-top: 8px; }}
          .mtile .m-sub {{ color: {SUBTLE}; font-size: .8rem; margin-top: 2px; }}
          .mtile .m-bar {{ height: 5px; border-radius: 999px; background: {HAIRLINE}; margin-top: 12px;
                           overflow: hidden; }}
          .mtile .m-bar > span {{ display:block; height:100%; border-radius:999px; }}
          .dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

          /* KPI hero (upload tab) */
          .hero {{ display: flex; align-items: center; gap: 40px; flex-wrap: wrap; }}
          .hero .context {{ color: {SUBTLE}; font-size: .82rem; font-weight: 700;
                            text-transform: uppercase; letter-spacing: .1em; margin-bottom: 14px; }}
          .stats {{ display: flex; gap: 40px; flex-wrap: wrap; }}
          .stat .num {{ font-size: 2.1rem; font-weight: 600; color: {INK}; letter-spacing: -0.02em;
                        line-height: 1; font-variant-numeric: tabular-nums; }}
          .stat .lbl {{ color: {SUBTLE}; font-size: .9rem; margin-top: 6px; }}

          /* Streamlit widgets on dark */
          [data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden; border: 1px solid {HAIRLINE}; }}
          .stDownloadButton button, .stButton button {{
            border-radius: 980px; border: 1px solid {HAIRLINE};
            background: {CARD_HI}; color: {INK}; font-weight: 600; padding: .5rem 1.1rem; }}
          .stDownloadButton button:hover, .stButton button:hover {{ border-color: {BLUE}; color: {BLUE}; }}
          .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
          .stTabs [data-baseweb="tab"] {{ color: {SUBTLE}; }}
          .stTabs [aria-selected="true"] {{ color: {INK}; }}
        </style>
        """


def inject_css() -> None:
    st.markdown(stylesheet(), unsafe_allow_html=True)


def _ring_svg(pct: float, color: str) -> str:
    r, sw = 78, 14
    c = 2 * math.pi * r
    dash = c * max(0.0, min(pct, 100.0)) / 100.0
    return f"""
    <svg width="196" height="196" viewBox="0 0 196 196">
      <circle cx="98" cy="98" r="{r}" fill="none" stroke="{HAIRLINE}" stroke-width="{sw}"/>
      <circle cx="98" cy="98" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}"
              stroke-linecap="round" stroke-dasharray="{dash:.2f} {c:.2f}"
              transform="rotate(-90 98 98)" style="filter:drop-shadow(0 0 6px {color}aa)"/>
      <text x="98" y="94" text-anchor="middle" font-size="42" font-weight="600"
            fill="{INK}" style="font-family:{FONT};letter-spacing:-1px">{pct:.1f}<tspan font-size="20" dy="-14">%</tspan></text>
      <text x="98" y="122" text-anchor="middle" font-size="13" fill="{SUBTLE}"
            style="font-family:{FONT};letter-spacing:.5px">WITHIN SLA</text>
    </svg>
    """


def kpi_hero_html(result: dict) -> str:
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
              <div class="stat"><div class="num"><span class="dot" style="background:{GREEN}"></span> {result['within_sla']:,}</div>
                   <div class="lbl">Within SLA</div></div>
              <div class="stat"><div class="num"><span class="dot" style="background:{RED if result['outside_sla'] else HAIRLINE}"></span> {result['outside_sla']:,}</div>
                   <div class="lbl">Outside SLA</div></div>
            </div>
          </div>
        </div>
        """


def kpi_hero(result: dict) -> None:
    st.markdown(kpi_hero_html(result), unsafe_allow_html=True)
