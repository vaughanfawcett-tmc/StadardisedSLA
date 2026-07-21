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
# Instrument-panel micro-labels (eyebrows, KPI labels) use the system mono.
MONO = ('ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, '
        '"Liberation Mono", monospace')


def health_color(pct: float) -> str:
    if pct >= 98:
        return GREEN
    if pct >= 95:
        return AMBER
    return RED


def stylesheet() -> str:
    return f"""
        <style>
          html {{ color-scheme: dark; }}
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

          ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
          ::-webkit-scrollbar-track {{ background: transparent; }}
          ::-webkit-scrollbar-thumb {{ background: #2A3644; border-radius: 999px;
                                       border: 2px solid {CANVAS}; }}
          ::-webkit-scrollbar-thumb:hover {{ background: #364456; }}

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
          [data-testid="stCaptionContainer"] p {{ color: {SUBTLE}; }}
          hr {{ border-color: {HAIRLINE}; }}

          .eyebrow {{ color: {SUBTLE}; font-family: {MONO}; font-size: .68rem; font-weight: 600;
                      text-transform: uppercase; letter-spacing: .16em; margin: 30px 0 12px;
                      display: flex; align-items: center; gap: 10px; }}
          .eyebrow::after {{ content: ""; flex: 1; height: 1px;
                             background: linear-gradient(90deg, {HAIRLINE}, transparent); }}
          .section-label {{ color: {INK}; font-weight: 600; font-size: 1.05rem;
                            letter-spacing: -0.01em; margin: 6px 0 10px; }}

          .card {{ background: {CARD}; border-radius: 20px; padding: 24px 26px;
                   box-shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 18px 44px rgba(0,0,0,.5);
                   border: 1px solid {HAIRLINE}; }}

          /* KPI overview strip */
          .kpi {{ background: {CARD}; border-radius: 18px; padding: 18px 20px;
                  border: 1px solid {HAIRLINE}; position: relative; overflow: hidden;
                  box-shadow: 0 14px 34px rgba(0,0,0,.45);
                  transition: transform .25s ease, border-color .25s ease; }}
          .kpi:hover {{ transform: translateY(-2px); border-color: #33445C; }}
          .kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
                          background: var(--accent, {BLUE});
                          box-shadow: 0 0 16px 1px var(--accent, {BLUE}); }}
          .kpi .k-label {{ color: {SUBTLE}; font-family: {MONO}; font-size: .68rem; font-weight: 600;
                           text-transform: uppercase; letter-spacing: .12em; }}
          .kpi .k-value {{ color: {INK}; font-size: 2rem; font-weight: 650; letter-spacing: -.02em;
                           font-variant-numeric: tabular-nums; line-height: 1.05; margin-top: 8px; }}
          .kpi .k-foot {{ color: {SUBTLE}; font-size: .8rem; margin-top: 4px; }}

          /* metric tile with health bar */
          .mtile {{ background: {CARD}; border-radius: 18px; padding: 18px 20px;
                    border: 1px solid {HAIRLINE}; box-shadow: 0 14px 34px rgba(0,0,0,.45);
                    transition: transform .25s ease, border-color .25s ease; }}
          .mtile:hover {{ transform: translateY(-2px); border-color: #33445C; }}
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
          .hero .context {{ color: {SUBTLE}; font-family: {MONO}; font-size: .74rem; font-weight: 600;
                            text-transform: uppercase; letter-spacing: .14em; margin-bottom: 14px; }}
          .stats {{ display: flex; gap: 40px; flex-wrap: wrap; }}
          .stat .num {{ font-size: 2.1rem; font-weight: 600; color: {INK}; letter-spacing: -0.02em;
                        line-height: 1; font-variant-numeric: tabular-nums; }}
          .stat .lbl {{ color: {SUBTLE}; font-size: .9rem; margin-top: 6px; }}

          /* Tabs → segmented control (react-aria DOM, Streamlit ≥1.5x) */
          .stTabs [role="tablist"] {{
            gap: 4px; background: {CARD}; border: 1px solid {HAIRLINE};
            border-radius: 999px; padding: 4px; width: max-content; }}
          .stTabs [data-testid="stTab"] {{
            color: {SUBTLE}; border-radius: 999px; padding: 6px 18px;
            border-bottom: none; box-shadow: none;
            transition: color .2s ease, background .2s ease; }}
          .stTabs [data-testid="stTab"]::after {{ display: none; }}
          .stTabs [data-testid="stTab"]:hover {{ color: {INK}; background: transparent; }}
          .stTabs [data-testid="stTab"][aria-selected="true"] {{
            color: {INK}; background: {CARD_HI};
            box-shadow: 0 2px 10px rgba(0,0,0,.45), 0 1px 0 rgba(255,255,255,.04) inset; }}
          .stTabs [data-testid="stTab"] p {{ font-size: .92rem; font-weight: 600; }}
          .stTabs [class*="SelectionIndicator"] {{ display: none; }}

          /* Horizontal radio → pill toggle */
          [data-testid="stRadio"] [role="radiogroup"] {{ gap: 6px; }}
          [data-testid="stRadio"] [role="radiogroup"] label {{
            background: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 999px;
            padding: 5px 16px; margin: 0; cursor: pointer;
            transition: border-color .2s ease, background .2s ease; }}
          [data-testid="stRadio"] [role="radiogroup"] label:hover {{ border-color: #33445C; }}
          [data-testid="stRadio"] [role="radiogroup"] label > span:first-child {{
            position: absolute; width: 1px; height: 1px; overflow: hidden;
            clip: rect(0 0 0 0); white-space: nowrap; }}
          /* the visual radio circle lives beside the text, three divs deep */
          [data-testid="stRadio"] [role="radiogroup"] label > div > div > div:first-child {{
            display: none; }}
          [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {{
            background: rgba(10,132,255,.14); border-color: rgba(10,132,255,.55); }}
          [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {{
            color: {BLUE}; font-weight: 600; }}

          /* File uploader dropzone */
          [data-testid="stFileUploaderDropzone"] {{
            background: {CARD}; border: 1.5px dashed #33445C; border-radius: 16px;
            transition: border-color .2s ease, background .2s ease; }}
          [data-testid="stFileUploaderDropzone"]:hover {{
            border-color: {BLUE}; background: {CARD_HI}; }}
          [data-testid="stFileUploaderDropzone"] button {{
            border-radius: 980px; border: 1px solid {HAIRLINE};
            background: {CARD_HI}; color: {INK}; font-weight: 600; }}

          /* Expanders as cards */
          [data-testid="stExpander"] {{
            background: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 16px;
            overflow: hidden; }}
          [data-testid="stExpander"] details {{ border: none; background: transparent; }}
          [data-testid="stExpander"] summary {{ padding: 14px 18px; }}
          [data-testid="stExpander"] summary:hover {{ color: {BLUE}; }}
          [data-testid="stExpander"] summary p {{ font-weight: 600; }}

          /* Alerts (info/success/warning) */
          [data-testid="stAlertContainer"] {{
            background: {CARD}; border: 1px solid {HAIRLINE}; border-radius: 14px;
            color: {INK}; }}

          /* Selects */
          [data-baseweb="select"] > div {{
            background: {CARD_HI}; border-color: {HAIRLINE}; border-radius: 12px; }}
          [data-baseweb="popover"] [role="listbox"] {{
            background: {CARD_HI}; border: 1px solid {HAIRLINE}; border-radius: 12px; }}

          /* Tables, buttons */
          [data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden; border: 1px solid {HAIRLINE}; }}
          .stDownloadButton button, .stButton button {{
            border-radius: 980px; border: 1px solid {HAIRLINE};
            background: {CARD_HI}; color: {INK}; font-weight: 600; padding: .5rem 1.1rem;
            transition: border-color .2s ease, color .2s ease, box-shadow .2s ease; }}
          .stDownloadButton button:hover, .stButton button:hover {{
            border-color: {BLUE}; color: {BLUE}; box-shadow: 0 0 0 3px rgba(10,132,255,.15); }}

          button:focus-visible, [role="tab"]:focus-visible, a:focus-visible {{
            outline: 2px solid {BLUE}; outline-offset: 2px; }}

          @media (prefers-reduced-motion: reduce) {{
            * {{ transition: none !important; animation: none !important; }}
          }}
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
