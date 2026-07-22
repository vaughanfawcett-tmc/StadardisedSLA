# Standardised SLA Automation

Scalable SLA reporting platform. Ingests SLA report exports from Fresh and turns
them into structured, queryable KPI outputs. Built in phases; **Phase 1 (Core SLA
Reporting / MVP)** and **Phase 2 (report types + history)** are implemented.

## What Phase 1 does

1. **Upload** a Fresh SLA export (`.csv` or `.xlsx`).
2. **Validate & map** the file to a standard schema (header names may vary).
3. **Derive** per ticket: reporting month, company name, SLA status, SLA flag.
4. **Filter** by company and month.
5. **Report** the core KPIs: total tickets, within SLA, outside SLA, SLA %.

## What Phase 2 adds

- **Report types** — a *Report* dropdown on every view: Combined SLA (the
  Phase 1 rule), First response, Resolution, or Every response. Per-metric
  reports cover only tickets that actually carry that SLA target (status
  populated) and judge them on that field alone.
- **Persistent history** — every processed upload is snapshotted to a small
  SQLite DB (`data/history.db`, override with `SLA_HISTORY_DB`). The
  **History** tab shows the upload log, all-time KPIs and a cross-upload SLA
  trend. Duplicate files are deduped by hash; a re-export covering the same
  month supersedes the older snapshot. Only aggregates are stored (per
  report x company x month counts) — never raw ticket rows.
  Note: on Render's free tier the disk is ephemeral, so history survives
  restarts but not redeploys; point `SLA_HISTORY_DB` at a mounted disk for
  durability.

The KPI output matches the brief's contract:

```json
{ "company": "Mitie", "month": "2026-05", "total_tickets": 100,
  "within_sla": 98, "outside_sla": 2, "sla_percentage": 98 }
```

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501, upload an export, pick a company + month.

## Run the tests

```bash
python tests/test_core.py
```

Tests run the full pipeline against a real 6,941-row export and assert the exact
KPI counts.

## Architecture (separation of concerns)

```
config/                 # Configurable, no code changes needed
  field_mapping.json    #   Fresh header  -> standard field (handles export variability)
  sla_rules.json        #   the SLA breach rule
  company_mapping.json  #   email domain  -> company name
sla_core/               # Reusable, UI-agnostic core data model
  ingest.py             #   read + validate + map + derive  -> tidy per-ticket frame
  sla_engine.py         #   configurable SLA status derivation
  companies.py          #   domain -> company mapping
  aggregate.py          #   frame -> KPIs / breakdowns
app.py                  # Phase 1 Streamlit UI (thin layer over sla_core)
tests/test_core.py
```

The core returns one standardised per-ticket DataFrame. Everything else reads it,
so later phases add on without reworking the data model:

- **Phase 2 (visual analytics):** `by_month()` / `by_company()` already produce the
  trend + comparison tables; wire richer charts onto the same frame.
- **Phase 3 (AI insights):** feed the standardised frame + aggregates as context to
  an LLM prompt layer.

## SLA rule (baseline)

A ticket is **Outside SLA** if any of `first_response_status`,
`resolution_status`, or `every_response_status` equals `SLA Violated`; otherwise
**Within SLA**. Blank/missing status = not applicable. Edit `config/sla_rules.json`
to change the rule.

## Company mapping

Company is derived from the requester's email domain via
`config/company_mapping.json`. Internal (`tmc.co.uk`) and personal
(gmail/outlook/…) domains are grouped separately so they don't masquerade as a
client. Unmapped domains fall back to a prettified domain name. Add domains to the
config as new clients appear.

## Deploy (Render)

`render.yaml` is included. Point Render at this repo (or `render deploy`); it runs
`streamlit run app.py` on the injected `$PORT`. Matches the existing Render app
pattern.
