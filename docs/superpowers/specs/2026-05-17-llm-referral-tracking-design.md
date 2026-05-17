# LLM Referral Tracking — Design Spec

**Date:** 2026-05-17  
**Status:** Approved

---

## Problem

LLM-driven traffic to zenskar.com is invisible in current analytics. `ga4_referrer_breakdown` surfaces referrer domains when browsers send a referrer header, but copy-paste traffic from chat interfaces (Claude, ChatGPT, Gemini) arrives as "direct" — no referrer, no attribution. There is also no passive UTM signal in `llms.txt` for click-through cases where the referrer is preserved.

---

## Goals

1. Add best-effort UTM tagging to `llms.txt` so click-through traffic from LLMs is attributed in GA4 automatically.
2. Add a dedicated `ga4_llm_referrals` MCP tool that aggregates referrer-based LLM traffic across all known LLM domains in a single call.

---

## Out of Scope

- Platform-specific UTM tags per LLM (not feasible — LLMs surface one URL verbatim, no dynamic substitution).
- Tracking copy-paste LLM traffic (not solvable at the GA4 referrer layer; would require a separate survey/intent signal).
- Changes to any non-GA4 data source.

---

## Part 1 — `llms.txt` UTM Tagging

Append `?utm_source=llm&utm_medium=referral` to every URL in `llms.txt`.

- **Source:** `llm` — a synthetic source name that won't collide with real referrer domains.
- **Medium:** `referral` — consistent with how GA4 classifies inbound link traffic.
- No `utm_campaign` — keep it minimal; campaign can be added later if needed.

GA4 reads UTM params automatically from the landing URL. No GA4 configuration required.

**Limitation:** LLMs may rewrite URLs to clean versions, dropping UTMs. This is a passive best-effort signal, not a complete solution.

---

## Part 2 — `ga4_llm_referrals` MCP Tool

### GA4 client addition (`mcp_server/clients/ga4.py`)

Add a `_in_list_filter(field, values)` helper using GA4's native `Filter.InListFilter`. This matches a dimension against a list of values in a single filter expression — cleaner than building an OR group manually.

```python
def _in_list_filter(field: str, values: list[str]) -> FilterExpression:
    return FilterExpression(filter=Filter(
        field_name=field,
        in_list_filter=Filter.InListFilter(values=values),
    ))
```

### Tool registration (`mcp_server/tools/ga4_tools.py`)

New tool `ga4_llm_referrals` registered alongside existing GA4 tools.

**Signature:**
```python
def ga4_llm_referrals(
    start_date: str = "",
    end_date: str = "",
    country: str = "",
    limit: int = 20,
) -> str
```

**LLM domain list (hardcoded):**
```python
LLM_SOURCES = [
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
```

**Logic:**
1. Build a filter: `_in_list_filter("sessionSource", LLM_SOURCES)`.
2. AND with country filter if provided (via `_and_filters`).
3. Run one `run_report` call: metrics `sessions, totalUsers, engagementRate, keyEvents`; dimension `sessionSource`; ordered by sessions desc.
4. Sum `sessions`, `totalUsers`, `keyEvents` across all rows for aggregated totals.
5. Return aggregated totals + per-source rows.

**Output shape:**
```json
{
  "period": "2026-04-19 to 2026-05-17",
  "total_llm_sessions": 312,
  "total_llm_users": 287,
  "total_llm_key_events": 14,
  "source_count": 3,
  "sources": [
    {"sessionSource": "perplexity.ai", "sessions": 198, "totalUsers": 180, "engagementRate": 0.62, "keyEvents": 9},
    {"sessionSource": "chat.openai.com", "sessions": 89, "totalUsers": 83, "engagementRate": 0.55, "keyEvents": 4}
  ]
}
```

---

## Files Changed

| File | Change |
|---|---|
| `llms.txt` | Append `?utm_source=llm&utm_medium=referral` to all URLs |
| `mcp_server/clients/ga4.py` | Add `_in_list_filter` helper |
| `mcp_server/tools/ga4_tools.py` | Register `ga4_llm_referrals` tool |

No new files. No schema changes. No dependency additions.
