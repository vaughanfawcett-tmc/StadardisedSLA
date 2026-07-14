#!/usr/bin/env node
// generate.mjs — regenerate monitors.csv and per-app snippet lines from apps.json.
// Run:  node kit/generate.mjs
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const { apps } = JSON.parse(readFileSync(join(here, 'apps.json'), 'utf8'))

// 1) Better Stack import file
const rows = ['name,url,check_frequency,expected_status']
for (const a of apps) rows.push(`${a.id} — prod,${a.url},180,200`)
writeFileSync(join(here, 'monitors.csv'), rows.join('\n') + '\n')

// 2) Copy-paste analytics lines per app
console.log('\nBetter Stack import  ->  kit/monitors.csv  (' + apps.length + ' monitors)\n')
console.log('Per-app analytics config:')
for (const a of apps) {
  if (a.type === 'js') {
    console.log(`\n  ${a.id} (${a.platform}, JS):`)
    console.log(`    posthog.register({ app: '${a.id}', platform: '${a.platform}' });`)
  } else {
    console.log(`\n  ${a.id} (${a.platform}, Python):`)
    console.log(`    analytics.APP = "${a.id}"`)
  }
}
console.log('')
