"""Map an email address / domain to a company name."""
from __future__ import annotations

import re

from .config import company_mapping

_EMAIL_RE = re.compile(r"@([\w.-]+)")


def domain_of(email: str | None) -> str:
    if not email:
        return ""
    m = _EMAIL_RE.search(str(email).strip().lower())
    return m.group(1) if m else ""


def _prettify(domain: str) -> str:
    """Fallback company name for an unmapped domain: 'foo-bar.co.uk' -> 'Foo Bar'."""
    if not domain:
        return "Unknown"
    label = domain.split(".")[0]
    label = label.replace("-", " ").replace("_", " ")
    return label.title()


def company_for_email(email: str | None, cfg: dict | None = None) -> str:
    cfg = cfg or company_mapping()
    domain = domain_of(email)
    if not domain:
        return cfg.get("personal_label", "Personal / Unknown")
    if domain in set(cfg.get("internal_domains", [])):
        return cfg.get("internal_label", "TMC (Internal)")
    if domain in set(cfg.get("personal_domains", [])):
        return cfg.get("personal_label", "Personal / Unknown")
    mapped = cfg.get("domain_to_company", {}).get(domain)
    return mapped if mapped else _prettify(domain)
