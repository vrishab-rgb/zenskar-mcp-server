"""Shared helpers used by every tool module."""

import json
import logging
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
