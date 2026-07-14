"""SLA status derivation — the configurable baseline rule.

A ticket is OUTSIDE SLA if ANY configured status field holds a violation value
(default: 'SLA Violated'). Blank / missing status = not applicable = no breach.
This mirrors the current manual reporting process and is driven entirely by
``config/sla_rules.json``.
"""
from __future__ import annotations

import pandas as pd

from .config import sla_rules


def derive_sla(df: pd.DataFrame, rules: dict | None = None) -> pd.DataFrame:
    """Add ``sla_within_flag`` (Y/N) and ``sla_status`` columns to a standardised frame."""
    rules = rules or sla_rules()
    fields = [f for f in rules["status_fields"] if f in df.columns]
    violations = {v.strip().lower() for v in rules["violation_values"]}

    if fields:
        norm = df[fields].fillna("").astype(str).apply(lambda s: s.str.strip().str.lower())
        breached = norm.isin(violations).any(axis=1)
    else:
        breached = pd.Series(False, index=df.index)

    out = df.copy()
    out["sla_within_flag"] = (~breached).map({True: "Y", False: "N"})
    out["sla_status"] = breached.map(
        {False: rules.get("within_label", "Within SLA"),
         True: rules.get("outside_label", "Outside SLA")}
    )
    return out
