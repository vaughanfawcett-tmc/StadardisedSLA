"""SLA status derivation — the configurable baseline rule.

A ticket is OUTSIDE SLA if ANY configured status field holds a violation value
(default: 'SLA Violated'). Blank / missing status = not applicable = no breach.
This mirrors the current manual reporting process and is driven entirely by
``config/sla_rules.json``.
"""
from __future__ import annotations

import pandas as pd

from .config import sla_rules


def _norm(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    return df[fields].fillna("").astype(str).apply(lambda s: s.str.strip().str.lower())


def within_mask(df: pd.DataFrame, fields: list[str] | None = None,
                rules: dict | None = None) -> pd.Series:
    """Boolean mask: True where the ticket is within SLA for the given status
    fields (defaults to all configured fields — the combined rule)."""
    rules = rules or sla_rules()
    fields = [f for f in (fields if fields is not None else rules["status_fields"])
              if f in df.columns]
    if not fields:
        return pd.Series(True, index=df.index)
    violations = {v.strip().lower() for v in rules["violation_values"]}
    return ~_norm(df, fields).isin(violations).any(axis=1)


def applicable_mask(df: pd.DataFrame, fields: list[str]) -> pd.Series:
    """Boolean mask: True where at least one of the status fields is populated,
    i.e. the ticket actually carried that SLA target."""
    fields = [f for f in fields if f in df.columns]
    if not fields:
        return pd.Series(False, index=df.index)
    return (_norm(df, fields) != "").any(axis=1)


def derive_sla(df: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
    """Add ``sla_within_flag`` (Y/N) and ``sla_status`` columns to a standardised frame."""
    rules = rules or sla_rules()
    breached = ~within_mask(df, rules=rules)

    out = df.copy()
    out["sla_within_flag"] = (~breached).map({True: "Y", False: "N"})
    out["sla_status"] = breached.map(
        {False: rules.get("within_label", "Within SLA"),
         True: rules.get("outside_label", "Outside SLA")}
    )
    return out
