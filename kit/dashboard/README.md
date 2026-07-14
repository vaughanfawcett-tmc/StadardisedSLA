# SLA Dashboard — the custom unified UI

One Streamlit app that shows **uptime (Better Stack) + usage (PostHog)** in a single
branded view. Same stack as your other apps, so it deploys to Render exactly like them.

Uptime lights up as soon as it's deployed (that data already flows). Usage appears once
the three apps are instrumented.

## Run locally
```
pip install -r requirements.txt
export BETTERSTACK_API_TOKEN=...        # Better Stack → Settings → API tokens
export POSTHOG_PERSONAL_API_KEY=phx_... # PostHog → Settings → Personal API keys (scope: query:read)
python3 -m streamlit run sla_dashboard.py
```
With no tokens it still runs — each section shows a "add this key" prompt instead of data.

## Deploy to Render
1. Push this `dashboard/` folder to a Git repo (or add to an existing one).
2. Render → **New → Web Service** → point at the repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `streamlit run sla_dashboard.py --server.port $PORT --server.address 0.0.0.0`
5. **Environment** → add the four vars from `.env.example` (two are secrets you generate).
6. Deploy. Optionally add the dashboard's own URL as a 4th Better Stack monitor.

## The two tokens (you generate — they're powerful secrets)
- **BETTERSTACK_API_TOKEN** — read-only access to your monitors/SLA. Better Stack → Settings → API tokens.
- **POSTHOG_PERSONAL_API_KEY** (`phx_…`) — scope it to **query:read** only. PostHog → Settings → Personal API keys.

These are *not* the same as the public `phc_…` client key in the app kit — they can read your
account, so keep them in Render env vars, never in the code or the repo.
