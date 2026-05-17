from google.analytics.data_v1beta.types import Filter
from mcp_server.clients.ga4 import _in_list_filter


def test_in_list_filter_sets_field_name():
    result = _in_list_filter("sessionSource", ["perplexity.ai", "chat.openai.com"])
    assert result.filter.field_name == "sessionSource"


def test_in_list_filter_sets_values():
    values = ["perplexity.ai", "chat.openai.com", "claude.ai"]
    result = _in_list_filter("sessionSource", values)
    assert list(result.filter.in_list_filter.values) == values


def test_in_list_filter_single_value():
    result = _in_list_filter("sessionSource", ["perplexity.ai"])
    assert list(result.filter.in_list_filter.values) == ["perplexity.ai"]
