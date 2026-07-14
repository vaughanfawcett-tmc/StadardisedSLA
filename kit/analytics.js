// analytics.js — shared usage instrumentation for every JS app (Vercel / Render web).
// One PostHog project across all apps. Each app calls initAnalytics() once with its own name.
//
// Install:  npm i posthog-js
// Env var:  POSTHOG_KEY  (Vercel: NEXT_PUBLIC_POSTHOG_KEY / VITE_POSTHOG_KEY)

import posthog from 'posthog-js'

const HOST = 'https://eu.i.posthog.com' // this account is on PostHog EU Cloud

/**
 * Call once when the app boots.
 * @param {string} app       kebab-case app id, e.g. 'invoice-tool' — MUST match apps.json
 * @param {string} platform  'vercel' | 'render'
 * @param {string} [key]     PostHog project key; falls back to env vars
 */
export function initAnalytics(app, platform, key) {
  const apiKey =
    key ||
    (typeof process !== 'undefined' &&
      (process.env.NEXT_PUBLIC_POSTHOG_KEY || process.env.VITE_POSTHOG_KEY || process.env.POSTHOG_KEY))

  if (!apiKey) {
    console.warn('[analytics] no PostHog key found — skipping init')
    return
  }

  posthog.init(apiKey, {
    api_host: HOST,
    person_profiles: 'identified_only',
    loaded: (ph) => {
      // Stamp EVERY event with these two props — this is what makes the dashboard splittable by app.
      ph.register({ app, platform })
    },
  })
}

/** Track a usage event. Standard first event is 'app_opened'. */
export function track(event, props = {}) {
  posthog.capture(event, props)
}

export { posthog }
