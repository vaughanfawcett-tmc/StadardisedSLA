"""Ingestion layer: read a Fresh export (CSV/XLSX), validate, map to the
standard schema, derive fields, and compute SLA status.

Returns a tidy per-ticket DataFrame (the reusable core data model). Everything
downstream — Phase 1 KPIs, Phase 2 charts, Phase 3 AI context — reads this.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd

from .companies import company_for_email
from .config import field_mapping
from .sla_engine import derive_sla

# Standard schema the rest of the system relies on.
STANDARD_COLUMNS = [
    "ticket_id", "subject", "created_time", "created_date", "reporting_month",
    "company_name", "email", "group", "agent",
    "first_response_status", "resolution_status", "every_response_status",
]
# Fields that must be resolvable for the file to be considered valid.
REQUIRED_STANDARD_FIELDS = ["ticket_id", "created_time"]


class IngestError(ValueError):
    """Raised when an uploaded file cannot be ingested (bad type, missing fields)."""


@dataclass
class IngestResult:
    df: pd.DataFrame
    row_count: int
    resolved_fields: dict = field(default_factory=dict)
    missing_fields: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _parse_datetimes(series: pd.Series) -> pd.Series:
    """Parse Created-time values robustly across Fresh export formats.

    Freshdesk's native export is ISO ``YYYY-MM-DD HH:MM:SS``; some cleaned
    exports use ``DD/MM/YYYY HH:MM``. Parsing ISO with ``dayfirst=True`` would
    silently mis-assign the month (and drop day>12), so we try ISO first and
    only fall back to day-first parsing for values ISO couldn't handle.
    """
    s = series.astype(str).str.strip()
    iso = pd.to_datetime(s, errors="coerce", format="ISO8601")
    todo = iso.isna() & (s != "")
    if todo.any():
        fallback = pd.to_datetime(s[todo], errors="coerce", dayfirst=True)
        iso = iso.copy()
        iso[todo] = fallback
    return iso


def _read_raw(data: bytes, filename: str) -> pd.DataFrame:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    if name.endswith(".csv") or name == "":
        # utf-8-sig strips the BOM Fresh exports include.
        return pd.read_csv(io.BytesIO(data), dtype=str, encoding="utf-8-sig",
                           keep_default_na=False)
    raise IngestError(f"Unsupported file type: {filename!r}. Upload a .csv or .xlsx export.")


def _resolve_columns(raw: pd.DataFrame, mapping: dict) -> tuple[dict, list]:
    """Match standard fields to actual headers (case/space-insensitive)."""
    lookup = {str(c).strip().lower(): c for c in raw.columns}
    resolved, missing = {}, []
    for std, candidates in mapping.items():
        hit = next((lookup[c.strip().lower()] for c in candidates
                    if c.strip().lower() in lookup), None)
        if hit is not None:
            resolved[std] = hit
        else:
            missing.append(std)
    return resolved, missing


def load_standardised(data: bytes, filename: str) -> IngestResult:
    raw = _read_raw(data, filename)
    if raw.empty:
        raise IngestError("The uploaded file has no rows.")

    mapping = field_mapping()
    resolved, missing = _resolve_columns(raw, mapping)

    missing_required = [f for f in REQUIRED_STANDARD_FIELDS if f in missing]
    if missing_required:
        raise IngestError(
            "Required fields could not be found in the export: "
            + ", ".join(missing_required)
            + ". Check the file is a Fresh SLA export, or add header aliases to "
            "config/field_mapping.json."
        )

    df = pd.DataFrame(index=raw.index)
    for std in mapping:
        df[std] = raw[resolved[std]].astype(str).str.strip() if std in resolved else ""

    # Derived: created_date, reporting_month.
    created = _parse_datetimes(df["created_time"])
    df["created_date"] = created.dt.date
    df["reporting_month"] = created.dt.strftime("%Y-%m")

    warnings = []
    bad_dates = int(created.isna().sum())
    if bad_dates:
        warnings.append(f"{bad_dates} row(s) had an unparseable Created time and are "
                        "excluded from month-based filtering.")

    # Derived: company_name.
    df["company_name"] = df["email"].map(company_for_email)

    # Derived: SLA status + flag.
    df = derive_sla(df)

    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    ordered = STANDARD_COLUMNS + ["sla_within_flag", "sla_status"]
    df = df[ordered]

    return IngestResult(
        df=df,
        row_count=len(df),
        resolved_fields=resolved,
        missing_fields=missing,
        warnings=warnings,
    )
