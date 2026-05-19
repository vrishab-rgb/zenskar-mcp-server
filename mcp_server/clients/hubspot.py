"""HubSpot CRM API client (strictly READ-ONLY)."""

import logging
import re
import time

import requests

from mcp_server import config

logger = logging.getLogger(__name__)

_BASE = "https://api.hubapi.com"
_session_cache = None


def _session() -> requests.Session:
    """Get a cached requests session with auth headers."""
    global _session_cache
    if _session_cache is None:
        if not config.HUBSPOT_PAT:
            raise ValueError("HUBSPOT_PAT not set")
        _session_cache = requests.Session()
        _session_cache.headers.update({
            "Authorization": f"Bearer {config.HUBSPOT_PAT}",
            "Content-Type": "application/json",
        })
    return _session_cache


def strip_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    for old, new in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&nbsp;", " "), ("&#x27;", "'"), ("&quot;", '"')]:
        text = text.replace(old, new)
    return text.strip()


def _check_404(r, object_type: str, object_id: str) -> None:
    """Raise a descriptive ValueError on 404 instead of a generic HTTPError."""
    if r.status_code == 404:
        others = [t for t in ("deals", "companies", "contacts") if t != object_type]
        raise ValueError(
            f"{object_type.rstrip('s').capitalize()} ID {object_id!r} not found. "
            f"If this ID came from a {others[0]} or {others[1]} lookup, pass it to "
            f"hubspot_get_{others[0].rstrip('s')} or hubspot_get_{others[1].rstrip('s')} instead. "
            "Use hubspot_resolve_id to identify what object type an unknown ID belongs to."
        )
    r.raise_for_status()


def get_company(company_id: str, properties: list[str]) -> dict:
    """GET a company by ID with specified properties."""
    props = ",".join(properties)
    r = _session().get(f"{_BASE}/crm/v3/objects/companies/{company_id}?properties={props}")
    _check_404(r, "companies", company_id)
    data = r.json()
    result = {"id": data.get("id", company_id)}
    result.update(data.get("properties", {}))
    return result


def get_contact(contact_id: str, properties: list[str]) -> dict:
    """GET a contact by ID with specified properties."""
    props = ",".join(properties)
    r = _session().get(f"{_BASE}/crm/v3/objects/contacts/{contact_id}?properties={props}")
    _check_404(r, "contacts", contact_id)
    data = r.json()
    result = {"id": data.get("id", contact_id)}
    result.update(data.get("properties", {}))
    return result


def get_deal(deal_id: str, properties: list[str]) -> dict:
    """GET a deal by ID with specified properties."""
    props = ",".join(properties)
    r = _session().get(f"{_BASE}/crm/v3/objects/deals/{deal_id}?properties={props}")
    _check_404(r, "deals", deal_id)
    data = r.json()
    result = {"id": data.get("id", deal_id)}
    result.update(data.get("properties", {}))
    return result


def resolve_hubspot_id(unknown_id: str) -> dict:
    """Probe an unknown ID against deals, companies, and contacts to identify its type."""
    _NAME_PROPS = {
        "deals": "dealname",
        "companies": "name",
        "contacts": None,  # built from firstname + lastname
    }
    for obj_type in ("deals", "companies", "contacts"):
        r = _session().get(f"{_BASE}/crm/v3/objects/{obj_type}/{unknown_id}")
        if r.status_code == 200:
            p = r.json().get("properties", {})
            if obj_type == "contacts":
                name = f"{p.get('firstname') or ''} {p.get('lastname') or ''}".strip()
            else:
                name = p.get(_NAME_PROPS[obj_type]) or ""
            return {"id": unknown_id, "type": obj_type, "name": name}
        time.sleep(0.05)
    return {"id": unknown_id, "type": None, "error": "ID not found in deals, companies, or contacts"}


def search_deals(
    filter_groups: list[dict],
    properties: list[str],
    limit: int = 20,
    sort_by: str = "createdate",
) -> list[dict]:
    """Search deals with HubSpot filter groups (POST, read-only search)."""
    payload = {
        "filterGroups": filter_groups,
        "properties": properties,
        "sorts": [{"propertyName": sort_by, "direction": "DESCENDING"}],
        "limit": limit,
    }
    r = _session().post(f"{_BASE}/crm/v3/objects/deals/search", json=payload)
    r.raise_for_status()
    data = r.json()
    results = []
    for deal in data.get("results", []):
        entry = {"id": deal.get("id", "")}
        entry.update(deal.get("properties", {}))
        results.append(entry)
    return results


def get_company_contacts(company_id: str, limit: int = 5) -> list[dict]:
    """Get contacts associated with a company."""
    r = _session().get(f"{_BASE}/crm/v3/objects/companies/{company_id}/associations/contacts")
    r.raise_for_status()
    contact_ids = [str(c["id"]) for c in r.json().get("results", [])]

    default_props = [
        "firstname", "lastname", "email", "jobtitle",
        "hs_analytics_source", "hs_analytics_first_url", "hs_analytics_last_url",
        "hs_analytics_num_page_views",
    ]

    contacts = []
    for ctid in contact_ids[:limit]:
        time.sleep(0.1)
        r2 = _session().get(
            f"{_BASE}/crm/v3/objects/contacts/{ctid}?properties={','.join(default_props)}"
        )
        if r2.status_code != 200:
            continue
        cp = r2.json().get("properties", {})
        contacts.append({
            "id": ctid,
            "name": f"{cp.get('firstname', '') or ''} {cp.get('lastname', '') or ''}".strip(),
            "email": cp.get("email") or "",
            "title": cp.get("jobtitle") or "",
            "source": cp.get("hs_analytics_source") or "",
            "first_url": cp.get("hs_analytics_first_url") or "",
            "last_url": cp.get("hs_analytics_last_url") or "",
            "page_views": cp.get("hs_analytics_num_page_views") or "",
        })

    return contacts


def get_company_notes(company_id: str, limit: int = 8) -> list[dict]:
    """Get notes associated with a company."""
    r = _session().get(f"{_BASE}/crm/v3/objects/companies/{company_id}/associations/notes")
    r.raise_for_status()
    note_ids = [str(n["id"]) for n in r.json().get("results", [])]

    notes = []
    for nid in note_ids[:limit]:
        time.sleep(0.1)
        r2 = _session().get(
            f"{_BASE}/crm/v3/objects/notes/{nid}?properties=hs_timestamp,hs_note_body"
        )
        if r2.status_code != 200:
            continue
        np = r2.json().get("properties", {})
        body = strip_html(np.get("hs_note_body"))
        if body:
            notes.append({
                "timestamp": np.get("hs_timestamp", ""),
                "body": body,
            })

    return notes


def get_company_meetings(company_id: str, limit: int = 8) -> list[dict]:
    """Get meetings associated with a company."""
    r = _session().get(f"{_BASE}/crm/v3/objects/companies/{company_id}/associations/meetings")
    r.raise_for_status()
    meeting_ids = [str(m["id"]) for m in r.json().get("results", [])]

    meetings = []
    for mid in meeting_ids[:limit]:
        time.sleep(0.1)
        r2 = _session().get(
            f"{_BASE}/crm/v3/objects/meetings/{mid}?properties=hs_timestamp,hs_meeting_title,hs_meeting_body,hs_meeting_outcome"
        )
        if r2.status_code != 200:
            continue
        mp = r2.json().get("properties", {})
        meetings.append({
            "timestamp": mp.get("hs_timestamp", ""),
            "title": mp.get("hs_meeting_title") or "",
            "outcome": mp.get("hs_meeting_outcome") or "",
            "body": strip_html(mp.get("hs_meeting_body")),
        })

    return meetings


def search_objects(
    object_type: str,
    filter_groups: list[dict],
    properties: list[str],
    limit: int = 50,
    sort_by: str = "createdate",
    direction: str = "DESCENDING",
) -> list[dict]:
    """Generic search across crm/v3/objects/{type}/search."""
    payload = {
        "filterGroups": filter_groups,
        "properties": properties,
        "sorts": [{"propertyName": sort_by, "direction": direction}],
        "limit": min(limit, 100),
    }
    r = _session().post(f"{_BASE}/crm/v3/objects/{object_type}/search", json=payload)
    r.raise_for_status()
    data = r.json()
    out = []
    for obj in data.get("results", []):
        entry = {"id": obj.get("id", "")}
        entry.update(obj.get("properties", {}))
        out.append(entry)
    return out


def search_contacts(
    filter_groups: list[dict], properties: list[str],
    limit: int = 50, sort_by: str = "createdate",
) -> list[dict]:
    return search_objects("contacts", filter_groups, properties, limit, sort_by)


def search_companies(
    filter_groups: list[dict], properties: list[str],
    limit: int = 50, sort_by: str = "createdate",
) -> list[dict]:
    return search_objects("companies", filter_groups, properties, limit, sort_by)


def search_meetings(
    filter_groups: list[dict], properties: list[str],
    limit: int = 50, sort_by: str = "hs_timestamp",
) -> list[dict]:
    return search_objects("meetings", filter_groups, properties, limit, sort_by)


def get_associations(
    from_type: str, from_id: str, to_type: str, limit: int = 100,
) -> list[str]:
    """Return list of associated object IDs."""
    r = _session().get(
        f"{_BASE}/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}?limit={limit}"
    )
    if r.status_code != 200:
        return []
    return [str(item["id"]) for item in r.json().get("results", [])]


def get_deal_associations(deal_id: str) -> dict:
    """Return contacts + companies associated with a deal."""
    return {
        "deal_id": deal_id,
        "contact_ids": get_associations("deals", deal_id, "contacts"),
        "company_ids": get_associations("deals", deal_id, "companies"),
    }


def get_contact_associations(contact_id: str) -> dict:
    """Return companies + deals associated with a contact."""
    return {
        "contact_id": contact_id,
        "company_ids": get_associations("contacts", contact_id, "companies"),
        "deal_ids": get_associations("contacts", contact_id, "deals"),
    }


def get_company_deals(company_id: str, properties: list[str] | None = None) -> list[dict]:
    """Hydrated deals associated with a company."""
    deal_ids = get_associations("companies", company_id, "deals")
    props = properties or [
        "dealname", "amount", "dealstage", "pipeline", "createdate", "closedate", "primary_source",
    ]
    deals = []
    for did in deal_ids:
        time.sleep(0.1)
        try:
            deals.append(get_deal(did, props))
        except Exception as e:
            logger.warning(f"failed deal {did}: {e}")
    return deals


def _fetch_form_submissions(form_guid: str) -> list[dict]:
    """Fetch all recent submissions for a form (requires `forms` scope on the PAT)."""
    r = _session().get(
        f"{_BASE}/form-integrations/v1/submissions/forms/{form_guid}?limit=50"
    )
    if r.status_code == 403:
        logger.warning(
            "forms scope missing on HUBSPOT_PAT — field values unavailable. "
            "Add the 'forms' scope to your Private Access Token in HubSpot settings."
        )
        return []
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def _match_form_submission(submissions: list[dict], occurred_at_iso: str) -> dict:
    """Return field values from the submission closest in time to the event timestamp."""
    if not submissions or not occurred_at_iso:
        return {}
    try:
        import datetime
        evt_ms = (
            datetime.datetime.fromisoformat(occurred_at_iso.replace("Z", "+00:00"))
            .timestamp() * 1000
        )
        best = min(submissions, key=lambda s: abs(s.get("submittedAt", 0) - evt_ms))
        if abs(best.get("submittedAt", 0) - evt_ms) > 30_000:  # >30s gap → no confident match
            return {}
        return {v["name"]: v.get("value", "") for v in best.get("values", [])}
    except Exception:
        return {}


def get_contact_form_submissions(contact_id: str, limit: int = 50) -> list[dict]:
    """Form submission events for a contact, including field values when available."""
    url = (
        f"{_BASE}/events/v3/events?objectType=contact&objectId={contact_id}"
        f"&eventType=e_submitted_form&limit={min(limit, 50)}"
    )
    r = _session().get(url)
    if r.status_code != 200:
        return []

    # Cache per-form submissions to avoid redundant API calls across events
    _form_cache: dict[str, list[dict]] = {}

    out = []
    for evt in r.json().get("results", []):
        props = evt.get("properties", {})
        occurred_at = evt.get("occurredAt", "")
        form_guid = props.get("hs_form_guid") or ""

        field_values: dict = {}
        if form_guid:
            if form_guid not in _form_cache:
                time.sleep(0.1)
                _form_cache[form_guid] = _fetch_form_submissions(form_guid)
            field_values = _match_form_submission(_form_cache[form_guid], occurred_at)

        out.append({
            "timestamp": occurred_at,
            "form_id": form_guid,
            "page_url": props.get("hs_url") or "",
            "page_title": props.get("hs_page_title") or "",
            "field_values": field_values,
        })
    return out


def get_contact_email_engagement(contact_id: str, limit: int = 50) -> list[dict]:
    """Email opens/clicks for a contact (best-effort across event types)."""
    out = []
    for ev_type in ("e_opened_email", "e_clicked_email", "e_sent_email", "e_delivered_email"):
        url = (
            f"{_BASE}/events/v3/events?objectType=contact&objectId={contact_id}"
            f"&eventType={ev_type}&limit={min(limit, 50)}"
        )
        r = _session().get(url)
        if r.status_code != 200:
            continue
        for evt in r.json().get("results", []):
            props = evt.get("properties", {})
            out.append({
                "timestamp": evt.get("occurredAt", ""),
                "event_type": ev_type,
                "email_subject": props.get("hs_email_subject") or "",
                "campaign_id": props.get("hs_email_campaign_id") or "",
            })
        time.sleep(0.1)
    out.sort(key=lambda x: x["timestamp"], reverse=True)
    return out[:limit]


def get_contact_meetings(contact_id: str, limit: int = 20) -> list[dict]:
    """Meetings associated with a contact."""
    meeting_ids = get_associations("contacts", contact_id, "meetings", limit=limit)
    meetings = []
    for mid in meeting_ids[:limit]:
        time.sleep(0.1)
        r2 = _session().get(
            f"{_BASE}/crm/v3/objects/meetings/{mid}"
            f"?properties=hs_timestamp,hs_meeting_title,hs_meeting_outcome,hs_meeting_body"
        )
        if r2.status_code != 200:
            continue
        mp = r2.json().get("properties", {})
        meetings.append({
            "timestamp": mp.get("hs_timestamp", ""),
            "title": mp.get("hs_meeting_title") or "",
            "outcome": mp.get("hs_meeting_outcome") or "",
            "body": strip_html(mp.get("hs_meeting_body")),
        })
    return meetings


def get_deal_activity_timeline(deal_id: str, limit: int = 25) -> dict:
    """Notes + meetings + calls associated with a deal, sorted by time."""
    out = {"deal_id": deal_id, "notes": [], "meetings": [], "calls": []}

    note_ids = get_associations("deals", deal_id, "notes", limit=limit)
    for nid in note_ids[:limit]:
        time.sleep(0.1)
        r = _session().get(f"{_BASE}/crm/v3/objects/notes/{nid}?properties=hs_timestamp,hs_note_body")
        if r.status_code != 200:
            continue
        np = r.json().get("properties", {})
        body = strip_html(np.get("hs_note_body"))
        if body:
            out["notes"].append({"timestamp": np.get("hs_timestamp", ""), "body": body})

    mtg_ids = get_associations("deals", deal_id, "meetings", limit=limit)
    for mid in mtg_ids[:limit]:
        time.sleep(0.1)
        r = _session().get(
            f"{_BASE}/crm/v3/objects/meetings/{mid}"
            f"?properties=hs_timestamp,hs_meeting_title,hs_meeting_outcome"
        )
        if r.status_code != 200:
            continue
        mp = r.json().get("properties", {})
        out["meetings"].append({
            "timestamp": mp.get("hs_timestamp", ""),
            "title": mp.get("hs_meeting_title") or "",
            "outcome": mp.get("hs_meeting_outcome") or "",
        })

    call_ids = get_associations("deals", deal_id, "calls", limit=limit)
    for cid in call_ids[:limit]:
        time.sleep(0.1)
        r = _session().get(
            f"{_BASE}/crm/v3/objects/calls/{cid}"
            f"?properties=hs_timestamp,hs_call_title,hs_call_disposition,hs_call_duration"
        )
        if r.status_code != 200:
            continue
        cp = r.json().get("properties", {})
        out["calls"].append({
            "timestamp": cp.get("hs_timestamp", ""),
            "title": cp.get("hs_call_title") or "",
            "disposition": cp.get("hs_call_disposition") or "",
            "duration_ms": cp.get("hs_call_duration") or "",
        })

    return out


def get_pipeline_summary(
    filter_groups: list[dict], group_by: str, limit: int = 200,
) -> list[dict]:
    """Pull deals matching filters; aggregate count + amount by group_by property."""
    props = ["amount", "dealstage", "pipeline", "primary_source", "closedate", group_by]
    deals = search_objects("deals", filter_groups, list(set(props)), limit=limit, sort_by="createdate")
    buckets: dict[str, dict] = {}
    for d in deals:
        key = d.get(group_by) or "(unset)"
        b = buckets.setdefault(key, {"group": key, "deal_count": 0, "amount_sum": 0.0})
        b["deal_count"] += 1
        try:
            b["amount_sum"] += float(d.get("amount") or 0)
        except (TypeError, ValueError):
            pass
    return sorted(buckets.values(), key=lambda r: r["deal_count"], reverse=True)


def get_field_coverage(
    object_type: str, properties: list[str], sample_size: int = 200,
) -> dict:
    """Sample N most recent records and report % populated for each property."""
    rows = search_objects(object_type, [], properties, limit=sample_size)
    total = len(rows)
    coverage = {}
    for p in properties:
        non_empty = sum(1 for r in rows if r.get(p) not in (None, "", []))
        coverage[p] = {
            "populated": non_empty,
            "total": total,
            "pct": round(non_empty / total * 100, 1) if total else 0.0,
        }
    return {"object_type": object_type, "sample_size": total, "coverage": coverage}


def get_property_distribution(
    object_type: str, property_name: str, sample_size: int = 500,
) -> dict:
    """Tally value counts for a property over recent records."""
    rows = search_objects(object_type, [], [property_name], limit=sample_size)
    counts: dict[str, int] = {}
    for r in rows:
        v = r.get(property_name)
        key = str(v) if v not in (None, "") else "(unset)"
        counts[key] = counts.get(key, 0) + 1
    distribution = sorted(
        [{"value": k, "count": v} for k, v in counts.items()],
        key=lambda x: x["count"], reverse=True,
    )
    return {
        "object_type": object_type, "property": property_name,
        "sample_size": len(rows), "distribution": distribution,
    }


def get_pages_to_deals(
    url_pattern: str, start_date: str | None = None, end_date: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Find contacts whose first/last URL contains a pattern, then their deals."""
    url_filter = {
        "filters": [
            {"propertyName": "hs_analytics_first_url", "operator": "CONTAINS_TOKEN", "value": url_pattern}
        ]
    }
    last_filter = {
        "filters": [
            {"propertyName": "hs_analytics_last_url", "operator": "CONTAINS_TOKEN", "value": url_pattern}
        ]
    }
    if start_date:
        url_filter["filters"].append({"propertyName": "createdate", "operator": "GTE", "value": start_date})
        last_filter["filters"].append({"propertyName": "createdate", "operator": "GTE", "value": start_date})
    if end_date:
        url_filter["filters"].append({"propertyName": "createdate", "operator": "LTE", "value": end_date})
        last_filter["filters"].append({"propertyName": "createdate", "operator": "LTE", "value": end_date})

    contact_props = [
        "firstname", "lastname", "email", "hs_analytics_first_url",
        "hs_analytics_last_url", "createdate",
    ]
    contacts = search_contacts(
        [url_filter, last_filter], contact_props, limit=limit, sort_by="createdate",
    )

    out = []
    for c in contacts:
        time.sleep(0.1)
        deal_ids = get_associations("contacts", c["id"], "deals")
        deals_summary = []
        for did in deal_ids[:5]:
            try:
                deals_summary.append(get_deal(did, ["dealname", "amount", "dealstage", "primary_source"]))
            except Exception:
                continue
        out.append({
            "contact_id": c["id"],
            "name": f"{c.get('firstname') or ''} {c.get('lastname') or ''}".strip(),
            "email": c.get("email") or "",
            "first_url": c.get("hs_analytics_first_url") or "",
            "last_url": c.get("hs_analytics_last_url") or "",
            "deals": deals_summary,
        })
    return out


def get_contact_page_visits(contact_id: str, limit: int = 50) -> list[dict]:
    """Get page visit events for a contact."""
    base_url = f"{_BASE}/events/v3/events?objectType=contact&objectId={contact_id}&eventType=e_visited_page&limit={min(limit, 50)}"

    events = []
    url = base_url
    while len(events) < limit:
        r = _session().get(url)
        if r.status_code != 200:
            break
        data = r.json()
        for evt in data.get("results", []):
            props = evt.get("properties", {})
            events.append({
                "timestamp": evt.get("occurredAt", ""),
                "url": props.get("hs_url") or "",
                "title": props.get("hs_page_title") or "",
                "referrer": props.get("hs_referrer") or "",
                "source": props.get("hs_visit_source") or "",
                "device": props.get("hs_device_type") or "",
                "country": props.get("hs_country") or "",
            })

        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        url = f"{base_url}&after={after}"
        time.sleep(0.1)

    events.sort(key=lambda x: x["timestamp"])
    return events[:limit]
