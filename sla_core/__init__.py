"""Standardised SLA — reusable core (ingestion → processing → aggregation).

UI-agnostic on purpose: Phase 1 (KPI UI), Phase 2 (charts) and Phase 3 (AI)
all build on the same standardised per-ticket DataFrame and these functions.
"""
from .aggregate import ALL, by_company, by_month, kpi, list_companies, list_months
from .ingest import IngestError, IngestResult, STANDARD_COLUMNS, load_standardised

__all__ = [
    "load_standardised", "IngestResult", "IngestError", "STANDARD_COLUMNS",
    "kpi", "by_company", "by_month", "list_companies", "list_months", "ALL",
]
