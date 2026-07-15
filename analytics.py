# analytics.py — shared usage instrumentation for every Streamlit app.
# One PostHog project across all apps. Drop this file next to your app and import it.
#
# Install:  add `posthog` to requirements.txt
# Secret:   set POSTHOG_KEY in Streamlit -> Settings -> Secrets  (or env var)
#
# Usage in streamlit_app.py:
#     import analytics
#     analytics.APP = "forecast-app"          # kebab-case, MUST match apps.json
#     analytics.page_open()                   # call once near the top
#     analytics.track("report_generated", rows=len(df))   # any custom event

import os
import uuid
import streamlit as st
from posthog import Posthog

APP = "CHANGE_ME"            # override from your app before calling track/page_open
HOST = "https://eu.i.posthog.com"   # this account is on PostHog EU Cloud


def _key() -> str | None:
    # Streamlit secrets first, then env var.
    try:
        if "POSTHOG_KEY" in st.secrets:
            return st.secrets["POSTHOG_KEY"]
    except Exception:
        pass
    return os.environ.get("POSTHOG_KEY")


@st.cache_resource
def _client() -> Posthog | None:
    key = _key()
    if not key:
        return None
    return Posthog(key, host=HOST)


def _pid() -> str:
    if "pid" not in st.session_state:
        st.session_state.pid = str(uuid.uuid4())
    return st.session_state.pid


def track(event: str, **props) -> None:
    """Track a usage event, stamped with app + platform like every other app.

    posthog>=7 signature: capture(event, distinct_id=..., properties=...).
    (Earlier positional form silently failed — the client swallows the error.)
    """
    client = _client()
    if client is None:
        return
    client.capture(event, distinct_id=_pid(),
                   properties={"app": APP, "platform": "streamlit", **props})


def page_open() -> None:
    """Fire the standard 'app_opened' event once per session."""
    if not st.session_state.get("_opened"):
        st.session_state["_opened"] = True
        track("app_opened")
