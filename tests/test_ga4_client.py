import pytest

from google.analytics.data_v1beta.types import Filter
from mcp_server.clients.ga4 import _in_list_filter


def test_in_list_filter_sets_field_name():
    result = _in_list_filter("sessionSource", ["perplexity.ai", "chat.openai.com"])
    assert result.filter.field_name == "sessionSource"


def test_in_list_filter_sets_values():
    values = ["perplexity.ai", "chat.openai.com", "claude.ai"]
    result = _in_list_filter("sessionSource", values)
    assert list(result.filter.in_list_filter.values) == values


def test_in_list_filter_empty_raises():
    with pytest.raises(ValueError, match="must be non-empty"):
        _in_list_filter("sessionSource", [])


def _aggregate_llm_rows(rows: list[dict]) -> dict:
    """Helper that mirrors the aggregation logic in ga4_llm_referrals."""
    total_sessions = sum(r.get("sessions", 0) for r in rows)
    total_users = sum(r.get("totalUsers", 0) for r in rows)
    total_key_events = sum(r.get("keyEvents", 0) for r in rows)
    return {
        "total_llm_sessions": total_sessions,
        "total_llm_users": total_users,
        "total_llm_key_events": total_key_events,
        "source_count": len(rows),
        "sources": rows,
    }


def test_llm_aggregation_sums_correctly():
    rows = [
        {"sessionSource": "perplexity.ai", "sessions": 198, "totalUsers": 180, "engagementRate": 0.62, "keyEvents": 9},
        {"sessionSource": "chat.openai.com", "sessions": 89, "totalUsers": 83, "engagementRate": 0.55, "keyEvents": 4},
    ]
    result = _aggregate_llm_rows(rows)
    assert result["total_llm_sessions"] == 287
    assert result["total_llm_users"] == 263
    assert result["total_llm_key_events"] == 13
    assert result["source_count"] == 2
    assert result["sources"] == rows


def test_llm_aggregation_empty_rows():
    result = _aggregate_llm_rows([])
    assert result["total_llm_sessions"] == 0
    assert result["total_llm_users"] == 0
    assert result["total_llm_key_events"] == 0
    assert result["source_count"] == 0
    assert result["sources"] == []
