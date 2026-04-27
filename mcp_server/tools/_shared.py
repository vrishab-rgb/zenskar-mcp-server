"""Shared helpers used by every tool module."""

import json
import logging
import re
from datetime import date, timedelta

logger = logging.getLogger("mcp_server")


def parse_dates(
    start_str: str, end_str: str, default_days: int = 28, lag_days: int = 0
) -> tuple[date, date]:
    """Parse date strings or default to last N days."""
    today = date.today()
    end = (
        date.fromisoformat(end_str)
        if end_str
        else today - timedelta(days=lag_days)
    )
    start = (
        date.fromisoformat(start_str)
        if start_str
        else end - timedelta(days=default_days)
    )
    return start, end


def ok(data) -> str:
    return json.dumps(data, indent=2, default=str)


def err(tool: str, ex: Exception) -> str:
    logger.exception(f"Tool {tool} failed")
    return json.dumps({"error": str(ex), "tool": tool})


DEFAULT_BRAND_TERMS = ["zenskar"]


def branded_filter(brand_terms: list[str] | None, included: bool = True) -> list[dict]:
    """GSC dimensionFilterGroups payload matching/excluding brand terms in `query`."""
    terms = brand_terms or DEFAULT_BRAND_TERMS
    op = "includingRegex" if included else "excludingRegex"
    pattern = "|".join(re.escape(t) for t in terms if t)
    return [{
        "filters": [{
            "dimension": "query",
            "operator": op,
            "expression": pattern,
        }]
    }]


def country_filter(country: str) -> list[dict] | None:
    """GSC dimensionFilterGroups payload for a 3-letter country code (e.g. 'usa')."""
    if not country:
        return None
    return [{
        "filters": [{
            "dimension": "country",
            "operator": "equals",
            "expression": country.lower(),
        }]
    }]


def period_compare(
    fetch_fn,
    start_a,
    end_a,
    start_b,
    end_b,
    key_field: str,
    metrics: tuple[str, ...] = ("clicks", "impressions", "ctr", "position"),
    sort_by: str = "clicks_change",
    limit: int = 50,
) -> list[dict]:
    """Generic two-window diff. fetch_fn(start, end) -> list[dict] with key_field + metrics."""
    rows_a = fetch_fn(start_a, end_a) or []
    rows_b = fetch_fn(start_b, end_b) or []
    map_a = {r.get(key_field): r for r in rows_a if r.get(key_field) is not None}
    map_b = {r.get(key_field): r for r in rows_b if r.get(key_field) is not None}

    compared = []
    for key in set(map_a) | set(map_b):
        ra = map_a.get(key, {})
        rb = map_b.get(key, {})
        entry = {key_field: key}
        for m in metrics:
            va = ra.get(m, 0) or 0
            vb = rb.get(m, 0) or 0
            entry[f"p1_{m}"] = va
            entry[f"p2_{m}"] = vb
            entry[f"{m}_change"] = round(vb - va, 4)
            if va:
                entry[f"{m}_change_pct"] = round((vb - va) / va * 100, 1)
        compared.append(entry)

    compared.sort(key=lambda x: abs(x.get(sort_by, 0) or 0), reverse=True)
    return compared[:limit]
