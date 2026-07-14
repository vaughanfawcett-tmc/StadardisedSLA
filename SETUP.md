# Standardised SLA — Setup

One usage + uptime dashboard for every app, whether it's on Render, Streamlit, or Vercel.
Unify at the **app layer** (same analytics in every app) and the **network layer** (one monitor per URL) — never platform by platform.

The `kit/` folder is done and ready. The only things left are the steps that need *your* login.

---

## Legend
- ✅ **Built for you** — files already in `kit/`, drop straight in.
- 🔑 **Needs your login** — I can't create accounts or paste your keys; walk through these (5 min each). Offer stands to do them live with you in the browser.
- ✏️ **Needs your inputs** — fill `kit/apps.json` with your real apps, then everything else regenerates.

---

## Step 1 — ✏️ Fill in your apps
Edit `kit/apps.json` — one entry per app (`id`, `url`, `platform`, `type`). Then:

```
node kit/generate.mjs
```

This rewrites `kit/monitors.csv` and prints the exact analytics line for each app.

## Step 2 — ✅ PostHog project (connected)
- Region: **EU Cloud** → `api_host` = `https://eu.i.posthog.com`
- Project ID: **217283**
- Project token (write-only client key, safe in public apps): `phc_sKVZdGbRuAsYc3syaFWWd7rV9K7GezJrYJFdi8mg4Mbe`
- Already baked into `kit/analytics.js`, `kit/analytics.py`, `kit/snippet.html`.

## Step 3 — ✅ Instrument each app (paste the kit)
- **JS apps (Vercel / Render):** either
  - add `kit/analytics.js` + `npm i posthog-js`, call `initAnalytics('<id>', '<platform>')` at boot, or
  - paste `kit/snippet.html` into `<head>` (no build step).
- **Streamlit apps:** copy `kit/analytics.py` next to your app, set `analytics.APP = "<id>"`, call `analytics.page_open()` near the top. Add `posthog` to `requirements.txt`.
- Put the key in each host's env/secrets as `POSTHOG_KEY` (Vercel: `NEXT_PUBLIC_POSTHOG_KEY`).

Then open each app once and confirm events appear in PostHog → Activity.

## Step 4 — ✅ Uptime monitors (created & live)
Better Stack team `t565925`. All three checked every 3 min, e-mail alert, 2-min confirmation delay
so Render cold starts don't trigger false "down" incidents:

| Monitor | URL | ID | Status |
|---------|-----|----|--------|
| `mileage-variance — prod` | https://mileagevarience.onrender.com | 4637161 | 🟢 Up |
| `mileage-variance-elia — prod` | https://mileagevarience-elia.onrender.com | 4637174 | 🟢 Up |
| `hsbc-sla-tool — prod` | https://hsbc-sla-tool.onrender.com | 4637182 | 🟢 Up |

Side benefit: 3-min checks keep the free Render apps warm (they idle-sleep after ~15 min), so users
hit fewer cold starts too.

Still optional: publish a **status page** (public SLA view) — not done yet because it publishes a
public URL; say the word and I'll set it up. You can also delete the sample `google.com` monitor.

## Step 5 — ✅ Custom unified UI (built)
A real dashboard app that pulls **both** APIs into one branded view lives in `kit/dashboard/`.
Verified it boots and renders; degrades gracefully when a token or data is missing.
- `sla_dashboard.py` — the Streamlit app (uptime tiles + usage tiles + trend chart, split by app)
- `requirements.txt`, `.env.example`, `README.md` (Render deploy steps)

To make it show **live** data it needs two secrets you generate (they can read your accounts,
so you create them — I don't):
- `BETTERSTACK_API_TOKEN` — Better Stack → Settings → API tokens
- `POSTHOG_PERSONAL_API_KEY` (`phx_…`, scope `query:read`) — PostHog → Settings → Personal API keys

Deploy it to Render like your other apps (see `kit/dashboard/README.md`). Uptime shows
immediately; usage shows once the apps are instrumented (Step 3).

Alternative if you don't want a 4th app: use PostHog's own dashboard (insights broken down by
`app`) + the Better Stack status page, side by side.

## Keeping it standard
Every event carries `app` + `platform`; every monitor is named `<id> — prod`. To add an app: add it to `apps.json`, rerun the generator, paste the snippet. It shows up in both dashboards automatically.

---

## What only you can do (and why)
| Step | Why it needs you |
|------|------------------|
| Create PostHog / Better Stack accounts | Signup + email verification under your identity |
| Provide the `phc_…` key | It's revealed only inside your account |
| Deploy the instrumented apps | Pushing to your Render / Streamlit / Vercel projects |

Everything else is in `kit/`. Give me your real app list (name · URL · Vercel/Render/Streamlit) and I'll fill `apps.json` and tailor each snippet exactly. Or say the word and I'll drive the two signups with you in the browser.
