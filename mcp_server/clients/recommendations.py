"""Supabase-backed recommendation registry client.

Used by the recommendations_* MCP tools. Sync only — matches the rest of the
server. Lazy-init Supabase client singleton.

Outcome computation reuses the existing gsc / ga4 / google_ads / hubspot client
modules — windows are computed here, raw data fetching is delegated.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from supabase import Client, create_client

from mcp_server import config

logger = logging.getLogger("mcp_server.recommendations")

_client: Client | None = None


def get_client() -> Client:
    """Lazy-init Supabase client. Raises if env vars not set."""
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    return _client


# ── CRUD wrappers ───────────────────────────────────────────────


def list_recs(
    status: str = "",
    rec_type: str = "",
    subject_contains: str = "",
    since: str = "",
    until: str = "",
    limit: int = 50,
) -> list[dict]:
    """Filter recommendations by structured fields. Newest date_raised first."""
    q = get_client().table("recommendations").select("*")
    if status:
        q = q.eq("status", status)
    if rec_type:
        q = q.eq("rec_type", rec_type)
    if subject_contains:
        q = q.ilike("subject", f"%{subject_contains}%")
    if since:
        q = q.gte("date_raised", since)
    if until:
        q = q.lte("date_raised", until)
    return q.order("date_raised", desc=True).limit(limit).execute().data


def get_rec(rec_id: int) -> dict | None:
    rows = (
        get_client()
        .table("recommendations")
        .select("*")
        .eq("id", rec_id)
        .execute()
        .data
    )
    return rows[0] if rows else None


def add_rec(fields: dict) -> dict:
    resp = get_client().table("recommendations").insert(fields).execute()
    return resp.data[0] if resp.data else {}


def update_rec(rec_id: int, fields: dict) -> dict:
    resp = (
        get_client()
        .table("recommendations")
        .update(fields)
        .eq("id", rec_id)
        .execute()
    )
    return resp.data[0] if resp.data else {}


def outcomes_pending() -> list[dict]:
    """Recs marked done, no outcome yet, treatment window has ended."""
    today = date.today().isoformat()
    return (
        get_client()
        .table("recommendations")
        .select("*")
        .eq("status", "done")
        .is_("outcome", "null")
        .lte("measure_after_date", today)
        .order("measure_after_date")
        .execute()
        .data
    )


def query_select(sql: str) -> list[dict]:
    """Run a SELECT-only SQL query via the exec_recommendations_select RPC.

    Validation lives in the SQL function (server-side). Stacked statements,
    non-SELECT keywords, and writes are rejected before execution.
    """
    resp = get_client().rpc("exec_recommendations_select", {"query_text": sql}).execute()
    return resp.data or []


# ── Window math + status transitions ────────────────────────────


def compute_measure_after_date(
    done_at: datetime, spec: dict | None
) -> str | None:
    """Given a done_at and a measurement_spec, return the date when the
    treatment window has fully elapsed (ISO date string), or None if no spec."""
    if not spec:
        return None
    lag = int(spec.get("lag_weeks", 0))
    treatment = int(spec.get("treatment_weeks", 4))
    d = done_at.date() if isinstance(done_at, datetime) else done_at
    return (d + timedelta(days=(lag + treatment) * 7)).isoformat()


# ── Outcome computation ─────────────────────────────────────────


def compute_outcome(rec: dict) -> dict:
    """Compute outcome for a done rec by querying the relevant data source.

    Idempotent — repeat calls produce the same outcome (modulo measured_at).
    Writes the outcome JSON back to the row. Returns the outcome dict.
    """
    spec = rec.get("measurement_spec")
    if not spec:
        raise ValueError(
            f"Rec {rec['id']} has no measurement_spec — outcome cannot be auto-measured"
        )
    if not rec.get("done_at"):
        raise ValueError(f"Rec {rec['id']} is not marked done — done_at is null")

    done_at = rec["done_at"]
    if isinstance(done_at, str):
        done_at = datetime.fromisoformat(done_at.replace("Z", "+00:00"))

    baseline_weeks = int(spec.get("baseline_weeks", 4))
    lag_weeks = int(spec.get("lag_weeks", 0))
    treatment_weeks = int(spec.get("treatment_weeks", 4))

    d = done_at.date() if isinstance(done_at, datetime) else done_at
    baseline_end = d
    baseline_start = d - timedelta(days=baseline_weeks * 7)
    treatment_start = d + timedelta(days=lag_weeks * 7)
    treatment_end = treatment_start + timedelta(days=treatment_weeks * 7)

    if treatment_end > date.today():
        raise ValueError(
            f"Treatment window not yet ended (ends {treatment_end}, today {date.today()})"
        )

    source = (spec.get("source") or "").lower()
    metrics = spec.get("metric") or []
    filters = spec.get("filter") or {}

    if source == "gsc":
        baseline = _measure_gsc(baseline_start, baseline_end, filters)
        treatment = _measure_gsc(treatment_start, treatment_end, filters)
        confounders = ["seasonality", "SERP/algorithm volatility — cannot attribute causally"]
    elif source == "ga4":
        baseline = _measure_ga4(baseline_start, baseline_end, metrics, filters)
        treatment = _measure_ga4(treatment_start, treatment_end, metrics, filters)
        confounders = ["seasonality", "site-wide traffic shifts"]
    elif source == "ads":
        baseline = _measure_ads(baseline_start, baseline_end, metrics, filters)
        treatment = _measure_ads(treatment_start, treatment_end, metrics, filters)
        confounders = ["competitor bidding shifts", "ad budget changes"]
    elif source == "hubspot":
        baseline = _measure_hubspot(baseline_start, baseline_end, metrics, filters)
        treatment = _measure_hubspot(treatment_start, treatment_end, metrics, filters)
        confounders = ["sample size", "marketing campaign overlap"]
    else:
        raise ValueError(f"Unsupported measurement source: {source!r}")

    delta: dict[str, float] = {}
    delta_pct: dict[str, float] = {}
    for k, b_val in baseline.items():
        if k in {"n_days"}:
            continue
        t_val = treatment.get(k)
        if isinstance(b_val, (int, float)) and isinstance(t_val, (int, float)):
            delta[k] = round(t_val - b_val, 2)
            if b_val:
                delta_pct[k] = round(((t_val - b_val) / b_val) * 100, 2)

    if source == "hubspot":
        small = baseline.get("n", 0) < 10 or treatment.get("n", 0) < 10
        if small:
            confounders.append(
                f"sample size small (n_baseline={baseline.get('n')}, n_treatment={treatment.get('n')})"
            )

    outcome = {
        "baseline": baseline,
        "treatment": treatment,
        "delta": delta,
        "delta_pct": delta_pct,
        "windows": {
            "baseline_start": baseline_start.isoformat(),
            "baseline_end": baseline_end.isoformat(),
            "treatment_start": treatment_start.isoformat(),
            "treatment_end": treatment_end.isoformat(),
        },
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "confounders_to_consider": confounders,
        "qualitative_note": (
            f"Observed change. Baseline {baseline_start} to {baseline_end}, "
            f"treatment {treatment_start} to {treatment_end}. "
            "This is correlation, not attributed lift."
        ),
    }

    update_rec(rec["id"], {"outcome": outcome})
    return outcome


# ── Per-source measurement helpers ──────────────────────────────


def _measure_gsc(start: date, end: date, filters: dict) -> dict:
    """Aggregate GSC clicks/impressions over the window with optional page+country filters."""
    from mcp_server.clients import gsc

    page = filters.get("page", "")
    country = filters.get("country", "")

    fg = []
    if page:
        fg.append({
            "filters": [{
                "dimension": "page",
                "operator": "equals",
                "expression": _full_url(page),
            }]
        })
    if country:
        fg.append({
            "filters": [{
                "dimension": "country",
                "operator": "equals",
                "expression": country.lower(),
            }]
        })

    rows = gsc.fetch_search_analytics(
        start, end,
        dimensions=["date"],
        dimension_filter_groups=fg or None,
        row_limit=10000,
    )

    clicks = sum(r.get("clicks", 0) for r in rows)
    impressions = sum(r.get("impressions", 0) for r in rows)
    if impressions:
        weighted_pos = sum(r.get("position", 0) * r.get("impressions", 0) for r in rows) / impressions
    else:
        weighted_pos = 0.0
    ctr = clicks / impressions if impressions else 0.0

    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(ctr, 4),
        "position": round(weighted_pos, 2),
        "n_days": (end - start).days,
    }


def _measure_ga4(start: date, end: date, metrics: list[str], filters: dict) -> dict:
    """Sum GA4 metrics over the window with optional pagePath + country filters.

    Filters in Python after fetch (small dataset for single-page queries)."""
    from mcp_server.clients import ga4

    page = filters.get("pagePath") or filters.get("page", "")
    country = filters.get("country", "")

    metric_aliases = {
        "users": "totalUsers",
        "conversionRate": "sessionConversionRate",
    }
    ga4_metrics = [metric_aliases.get(m, m) for m in metrics] or ["sessions", "totalUsers"]

    dims: list[str] = []
    if page:
        dims.append("pagePath")
    if country:
        dims.append("country")
    if not dims:
        dims = ["pagePath"]

    rows = ga4.run_report(
        start, end, metrics=ga4_metrics, dimensions=dims, limit=10000,
    )

    def matches(r: dict) -> bool:
        if page and r.get("pagePath", "") != page:
            return False
        if country and r.get("country", "") != country:
            return False
        return True

    matching = [r for r in rows if matches(r)]
    result: dict = {"n_days": (end - start).days}
    for m in ga4_metrics:
        result[m] = sum(float(r.get(m, 0) or 0) for r in matching)
    return result


def _measure_ads(start: date, end: date, metrics: list[str], filters: dict) -> dict:
    """Sum Ads metrics across campaigns matching the campaign filter."""
    from mcp_server.clients import google_ads

    campaign = filters.get("campaign", "")
    rows = google_ads.fetch_campaigns(start, end)

    if campaign:
        rows = [r for r in rows if r.get("name", "") == campaign]

    result: dict = {"n_days": (end - start).days}
    for m in metrics or ["clicks", "impressions", "cost", "conversions"]:
        result[m] = sum(float(r.get(m, 0) or 0) for r in rows)
    return result


def _measure_hubspot(start: date, end: date, metrics: list[str], filters: dict) -> dict:
    """Count + sum HubSpot deals matching the filter, within the window."""
    from mcp_server.clients import hubspot

    extra_filters = filters.get("filter_groups") or []
    source = filters.get("source", "")

    base_filters: list[dict] = []
    if source:
        base_filters.append({
            "propertyName": "hs_analytics_source",
            "operator": "EQ",
            "value": source,
        })
    base_filters.extend([
        {
            "propertyName": "createdate",
            "operator": "GTE",
            "value": str(int(datetime(start.year, start.month, start.day).timestamp() * 1000)),
        },
        {
            "propertyName": "createdate",
            "operator": "LT",
            "value": str(int(datetime(end.year, end.month, end.day).timestamp() * 1000)),
        },
    ])

    filter_groups = [{"filters": base_filters}]
    filter_groups.extend(extra_filters)

    properties = filters.get("properties") or ["dealname", "amount", "createdate", "dealstage"]
    rows = hubspot.search_deals(filter_groups, properties=properties, limit=200)

    result: dict = {"n": len(rows), "n_days": (end - start).days}
    if "amount" in (metrics or []) or "total_amount" in (metrics or []):
        result["total_amount"] = sum(float(r.get("amount") or 0) for r in rows)
    return result


def _full_url(page_path: str) -> str:
    """GSC's page filter expects full URLs (https://www.zenskar.com/x), not paths."""
    if page_path.startswith("http"):
        return page_path
    base = config.GSC_SITE_URL.rstrip("/")
    if not page_path.startswith("/"):
        page_path = "/" + page_path
    return base + page_path
