"""Configuration loading for the SLA core.

Configs live in ``config/*.json`` so ingestion mapping, SLA logic and company
mapping are all editable without touching code (a key design principle of the
brief). Built-in defaults are used if a file is missing, so the package works
standalone.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_DEFAULT_FIELD_MAPPING = {
    "ticket_id": ["Ticket ID", "Case Number", "CASE NUMBER", "ID"],
    "subject": ["Subject", "SUBCASE TITLE", "Summary"],
    "created_time": ["Created time", "Created Time", "Created"],
    "group": ["Group", "Team"],
    "agent": ["Agent"],
    "email": ["Contact ID", "EMAIL ADDRESS", "Email"],
    "first_response_status": ["First response status"],
    "resolution_status": ["Resolution status"],
    "every_response_status": ["Every response status"],
}

_DEFAULT_SLA_RULES = {
    "status_fields": [
        "first_response_status",
        "resolution_status",
        "every_response_status",
    ],
    "violation_values": ["SLA Violated"],
    "within_values": ["Within SLA"],
    "within_label": "Within SLA",
    "outside_label": "Outside SLA",
}

_DEFAULT_COMPANY_MAPPING = {
    "internal_label": "TMC (Internal)",
    "internal_domains": ["tmc.co.uk"],
    "personal_label": "Personal / Unknown",
    "personal_domains": ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"],
    "domain_to_company": {},
}


def _load(name: str, default: dict) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        return default
    data = json.loads(path.read_text())
    # Strip comment keys so they never leak into logic.
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=None)
def field_mapping() -> dict:
    return _load("field_mapping.json", _DEFAULT_FIELD_MAPPING)


@lru_cache(maxsize=None)
def sla_rules() -> dict:
    return _load("sla_rules.json", _DEFAULT_SLA_RULES)


@lru_cache(maxsize=None)
def company_mapping() -> dict:
    return _load("company_mapping.json", _DEFAULT_COMPANY_MAPPING)
