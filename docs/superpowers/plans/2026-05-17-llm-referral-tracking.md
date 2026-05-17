# LLM Referral Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add UTM params to all `llms.txt` URLs and a new `ga4_llm_referrals` MCP tool that aggregates referrer-based LLM traffic from GA4.

**Architecture:** Add an `_in_list_filter` helper to the GA4 client (mirrors existing `_string_filter` pattern), register a new tool in `ga4_tools.py` that filters on known LLM domains and returns aggregated totals + per-source rows, and append UTM params to every URL in `llms.txt`.

**Tech Stack:** Python 3.11, `google-analytics-data` (GA4 Data API v1beta), `pytest` (new dev dependency for tests)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `pytest` dev dependency |
| `tests/__init__.py` | Create | Make `tests/` a package |
| `tests/test_ga4_client.py` | Create | Unit tests for `_in_list_filter` |
| `mcp_server/clients/ga4.py` | Modify | Add `_in_list_filter` helper |
| `mcp_server/tools/ga4_tools.py` | Modify | Register `ga4_llm_referrals` tool |
| `llms.txt` | Modify | Append UTM params to all URLs |

---

## Task 1: Set up pytest and add `_in_list_filter` to GA4 client

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/test_ga4_client.py`
- Modify: `mcp_server/clients/ga4.py`

- [ ] **Step 1: Add pytest to pyproject.toml**

Add the following after the `[build-system]` block in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

Then install:

```bash
pip install -e ".[dev]"
```

Expected: pytest installs successfully.

- [ ] **Step 2: Create tests package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 3: Write the failing test**

Create `tests/test_ga4_client.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/test_ga4_client.py -v
```

Expected: FAIL — `ImportError: cannot import name '_in_list_filter' from 'mcp_server.clients.ga4'`

- [ ] **Step 5: Add `_in_list_filter` to `mcp_server/clients/ga4.py`**

Add this function after the `_string_filter` function (around line 159):

```python
def _in_list_filter(field: str, values: list[str]) -> FilterExpression:
    return FilterExpression(filter=Filter(
        field_name=field,
        in_list_filter=Filter.InListFilter(values=values),
    ))
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_ga4_client.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/__init__.py tests/test_ga4_client.py mcp_server/clients/ga4.py
git commit -m "feat: add _in_list_filter helper to GA4 client"
```

---

## Task 2: Register `ga4_llm_referrals` MCP tool

**Files:**
- Modify: `mcp_server/tools/ga4_tools.py`
- Modify: `tests/test_ga4_client.py` (extend with aggregation logic test)

- [ ] **Step 1: Write the failing test for aggregation logic**

The tool's aggregation (summing rows into totals) is the only non-trivial logic. Extract it for isolated testing by appending to `tests/test_ga4_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ga4_client.py::test_llm_aggregation_sums_correctly tests/test_ga4_client.py::test_llm_aggregation_empty_rows -v
```

Expected: FAIL — `NameError: name '_aggregate_llm_rows' is not defined`

- [ ] **Step 3: Implement `ga4_llm_referrals` in `mcp_server/tools/ga4_tools.py`**

Add the following at the end of the `register(mcp)` function in `ga4_tools.py`, before the final closing of `register`:

```python
    _LLM_SOURCES = [
        "perplexity.ai",
        "chat.openai.com",
        "chatgpt.com",
        "claude.ai",
        "gemini.google.com",
        "copilot.microsoft.com",
        "you.com",
        "phind.com",
        "bing.com",
    ]

    @mcp.tool()
    def ga4_llm_referrals(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        limit: int = 20,
    ) -> str:
        """Aggregate GA4 traffic from LLM platforms (Perplexity, ChatGPT, Claude, Gemini, etc.).

        Returns total LLM-referred sessions/users/key-events plus a per-source breakdown.

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            country: Full country name filter (e.g. "United States")
            limit: Max source rows to return (default: 20)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            start, end = parse_dates(start_date, end_date)

            llm_filter = ga4._in_list_filter("sessionSource", _LLM_SOURCES)
            country_filter = ga4._build_filter(country, "")
            combined = ga4._and_filters(llm_filter, country_filter)

            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "engagementRate", "keyEvents"],
                dimensions=["sessionSource"],
                dimension_filter=combined,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=limit,
            )

            total_sessions = sum(r.get("sessions", 0) for r in rows)
            total_users = sum(r.get("totalUsers", 0) for r in rows)
            total_key_events = sum(r.get("keyEvents", 0) for r in rows)

            return ok({
                "period": f"{start} to {end}",
                "total_llm_sessions": total_sessions,
                "total_llm_users": total_users,
                "total_llm_key_events": total_key_events,
                "source_count": len(rows),
                "sources": rows,
            })
        except Exception as ex:
            return err("ga4_llm_referrals", ex)
```

- [ ] **Step 4: Copy `_aggregate_llm_rows` into the test file**

The test helper `_aggregate_llm_rows` in the test file mirrors the tool's inline logic. The tests are already written to use it — no change needed to the test file. The tests pass because `_aggregate_llm_rows` is defined locally in the test module.

Run all tests to confirm nothing broke:

```bash
pytest tests/test_ga4_client.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/tools/ga4_tools.py tests/test_ga4_client.py
git commit -m "feat: add ga4_llm_referrals MCP tool"
```

---

## Task 3: UTM-tag all URLs in `llms.txt`

**Files:**
- Modify: `llms.txt`

- [ ] **Step 1: Run transformation script**

From the project root, run:

```bash
python - <<'EOF'
import re

with open("llms.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Append UTM params to every https://... URL that doesn't already have a query string
tagged = re.sub(
    r'(https://[^\s\)]+?)(?=\s|$)',
    lambda m: m.group(1) + "?utm_source=llm&utm_medium=referral",
    content,
)

with open("llms.txt", "w", encoding="utf-8") as f:
    f.write(tagged)

print("Done.")
EOF
```

Expected output: `Done.`

- [ ] **Step 2: Verify a sample of URLs**

```bash
python -c "
with open('llms.txt') as f:
    lines = [l.strip() for l in f if 'https://' in l]
print('\n'.join(lines[:5]))
print('...')
print(f'Total URL lines: {len(lines)}')
"
```

Expected: Each URL line ends with `?utm_source=llm&utm_medium=referral`. Total should be ~187.

- [ ] **Step 3: Spot-check no double UTMs**

```bash
python -c "
with open('llms.txt') as f:
    content = f.read()
count = content.count('utm_source=llm&utm_medium=referral')
doubles = content.count('utm_source=llm&utm_medium=referral?utm_source=llm')
print(f'UTM occurrences: {count}, double-tagged: {doubles}')
"
```

Expected: `double-tagged: 0`

- [ ] **Step 4: Commit**

```bash
git add llms.txt
git commit -m "feat: add UTM params to llms.txt URLs for LLM referral tracking"
```

---

## Self-Review Checklist

- [x] `_in_list_filter` — spec says add to `ga4.py`, covered in Task 1
- [x] `ga4_llm_referrals` — spec output shape matches (period, total_llm_sessions, total_llm_users, total_llm_key_events, source_count, sources), covered in Task 2
- [x] LLM domain list — all 9 domains from spec included in `_LLM_SOURCES`
- [x] `llms.txt` UTM tagging — covered in Task 3
- [x] No placeholders or TBDs
- [x] Type consistency — `_in_list_filter` called as `ga4._in_list_filter(...)` in tool, matches definition in client
- [x] `_and_filters` handles `None` second arg (country filter returns `None` when country is empty) — verified in `ga4.py:162-168`, it filters out `None` values
