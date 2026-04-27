"""HubSpot CRM tools (READ-ONLY)."""

import json

from mcp_server.tools._shared import err, ok, parse_dates


def register(mcp) -> None:
    @mcp.tool()
    def hubspot_search_deals(
        filters: str = "[]",
        properties: str = "dealname,amount,dealstage,pipeline,createdate,closedate,primary_source",
        limit: int = 20,
        sort_by: str = "createdate",
    ) -> str:
        """Search HubSpot deals with filters (READ-ONLY).

        Args:
            filters: JSON string of HubSpot filter groups array. Example:
                '[{"filters":[{"propertyName":"dealstage","operator":"EQ","value":"closedwon"}]}]'
            properties: Comma-separated deal properties to return
            limit: Max deals to return (default: 20)
            sort_by: Property to sort by (default: "createdate")
        """
        try:
            from mcp_server.clients import hubspot

            filter_groups = json.loads(filters)
            props_list = [p.strip() for p in properties.split(",")]
            rows = hubspot.search_deals(filter_groups, props_list, limit=limit, sort_by=sort_by)
            return ok({"deal_count": len(rows), "deals": rows})
        except Exception as ex:
            return err("hubspot_search_deals", ex)

    @mcp.tool()
    def hubspot_get_company(
        company_id: str,
        properties: str = "name,domain,industry,numberofemployees,annualrevenue,country,city,description",
    ) -> str:
        """Get a HubSpot company by ID (READ-ONLY).

        Args:
            company_id: HubSpot company ID
            properties: Comma-separated properties to return
        """
        try:
            from mcp_server.clients import hubspot

            props_list = [p.strip() for p in properties.split(",")]
            result = hubspot.get_company(company_id, props_list)
            return ok(result)
        except Exception as ex:
            return err("hubspot_get_company", ex)

    @mcp.tool()
    def hubspot_get_contact(
        contact_id: str,
        properties: str = "firstname,lastname,email,jobtitle,hs_analytics_source,hs_analytics_first_url",
    ) -> str:
        """Get a HubSpot contact by ID (READ-ONLY).

        Args:
            contact_id: HubSpot contact ID
            properties: Comma-separated properties to return
        """
        try:
            from mcp_server.clients import hubspot

            props_list = [p.strip() for p in properties.split(",")]
            result = hubspot.get_contact(contact_id, props_list)
            return ok(result)
        except Exception as ex:
            return err("hubspot_get_contact", ex)

    @mcp.tool()
    def hubspot_get_deal(
        deal_id: str,
        properties: str = "dealname,amount,dealstage,closedate,primary_source,description",
    ) -> str:
        """Get a HubSpot deal by ID (READ-ONLY).

        Args:
            deal_id: HubSpot deal ID
            properties: Comma-separated properties to return
        """
        try:
            from mcp_server.clients import hubspot

            props_list = [p.strip() for p in properties.split(",")]
            result = hubspot.get_deal(deal_id, props_list)
            return ok(result)
        except Exception as ex:
            return err("hubspot_get_deal", ex)

    @mcp.tool()
    def hubspot_company_contacts(company_id: str, limit: int = 5) -> str:
        """Get contacts associated with a HubSpot company (READ-ONLY).

        Args:
            company_id: HubSpot company ID
            limit: Max contacts to return (default: 5)
        """
        try:
            from mcp_server.clients import hubspot

            contacts = hubspot.get_company_contacts(company_id, limit=limit)
            return ok({"company_id": company_id, "contact_count": len(contacts), "contacts": contacts})
        except Exception as ex:
            return err("hubspot_company_contacts", ex)

    @mcp.tool()
    def hubspot_company_activity(
        company_id: str,
        include_notes: bool = True,
        include_meetings: bool = True,
        limit: int = 5,
    ) -> str:
        """Get notes and meetings for a HubSpot company (READ-ONLY).

        Args:
            company_id: HubSpot company ID
            include_notes: Include notes (default: True)
            include_meetings: Include meetings (default: True)
            limit: Max items per type (default: 5)
        """
        try:
            from mcp_server.clients import hubspot

            result: dict = {"company_id": company_id}
            if include_notes:
                result["notes"] = hubspot.get_company_notes(company_id, limit=limit)
            if include_meetings:
                result["meetings"] = hubspot.get_company_meetings(company_id, limit=limit)
            return ok(result)
        except Exception as ex:
            return err("hubspot_company_activity", ex)

    @mcp.tool()
    def hubspot_contact_journey(contact_id: str, limit: int = 50) -> str:
        """Get page visit history for a HubSpot contact (READ-ONLY).

        Args:
            contact_id: HubSpot contact ID
            limit: Max page visits to return (default: 50)
        """
        try:
            from mcp_server.clients import hubspot

            events = hubspot.get_contact_page_visits(contact_id, limit=limit)
            return ok({"contact_id": contact_id, "visit_count": len(events), "visits": events})
        except Exception as ex:
            return err("hubspot_contact_journey", ex)

    def _build_date_filter_groups(
        existing_filters: str, created_after: str, created_before: str,
    ) -> list[dict]:
        """Merge user filters JSON with createdate range filters."""
        groups = json.loads(existing_filters) if existing_filters else []
        date_filters = []
        if created_after:
            date_filters.append({"propertyName": "createdate", "operator": "GTE", "value": created_after})
        if created_before:
            date_filters.append({"propertyName": "createdate", "operator": "LTE", "value": created_before})
        if not date_filters:
            return groups or [{"filters": []}]
        if not groups:
            return [{"filters": date_filters}]
        for g in groups:
            g.setdefault("filters", []).extend(date_filters)
        return groups

    @mcp.tool()
    def hubspot_search_contacts(
        filters: str = "[]",
        properties: str = "firstname,lastname,email,jobtitle,hs_analytics_source,hs_analytics_first_url,createdate",
        created_after: str = "",
        created_before: str = "",
        limit: int = 50,
    ) -> str:
        """Search HubSpot contacts with filters (READ-ONLY).

        Args:
            filters: JSON string of HubSpot filter groups array (default: "[]")
            properties: Comma-separated contact properties to return
            created_after: ISO date filter on createdate (>=)
            created_before: ISO date filter on createdate (<=)
            limit: Max contacts (default: 50)
        """
        try:
            from mcp_server.clients import hubspot

            groups = _build_date_filter_groups(filters, created_after, created_before)
            props_list = [p.strip() for p in properties.split(",")]
            rows = hubspot.search_contacts(groups, props_list, limit=limit)
            return ok({"contact_count": len(rows), "contacts": rows})
        except Exception as ex:
            return err("hubspot_search_contacts", ex)

    @mcp.tool()
    def hubspot_search_companies(
        filters: str = "[]",
        properties: str = "name,domain,industry,numberofemployees,annualrevenue,country,createdate",
        created_after: str = "",
        created_before: str = "",
        limit: int = 50,
    ) -> str:
        """Search HubSpot companies with filters (READ-ONLY).

        Args:
            filters: JSON string of HubSpot filter groups array
            properties: Comma-separated company properties
            created_after: ISO date filter (>=)
            created_before: ISO date filter (<=)
            limit: Max companies (default: 50)
        """
        try:
            from mcp_server.clients import hubspot

            groups = _build_date_filter_groups(filters, created_after, created_before)
            props_list = [p.strip() for p in properties.split(",")]
            rows = hubspot.search_companies(groups, props_list, limit=limit)
            return ok({"company_count": len(rows), "companies": rows})
        except Exception as ex:
            return err("hubspot_search_companies", ex)

    @mcp.tool()
    def hubspot_get_deal_associations(deal_id: str) -> str:
        """Get contacts and company associated with a HubSpot deal (READ-ONLY)."""
        try:
            from mcp_server.clients import hubspot
            return ok(hubspot.get_deal_associations(deal_id))
        except Exception as ex:
            return err("hubspot_get_deal_associations", ex)

    @mcp.tool()
    def hubspot_get_contact_associations(contact_id: str) -> str:
        """Get companies and deals associated with a HubSpot contact (READ-ONLY)."""
        try:
            from mcp_server.clients import hubspot
            return ok(hubspot.get_contact_associations(contact_id))
        except Exception as ex:
            return err("hubspot_get_contact_associations", ex)

    @mcp.tool()
    def hubspot_get_company_deals(
        company_id: str,
        properties: str = "dealname,amount,dealstage,pipeline,createdate,closedate,primary_source",
    ) -> str:
        """Get deals associated with a HubSpot company (READ-ONLY).

        Args:
            company_id: HubSpot company ID
            properties: Comma-separated deal properties
        """
        try:
            from mcp_server.clients import hubspot
            props_list = [p.strip() for p in properties.split(",")]
            deals = hubspot.get_company_deals(company_id, props_list)
            return ok({"company_id": company_id, "deal_count": len(deals), "deals": deals})
        except Exception as ex:
            return err("hubspot_get_company_deals", ex)

    @mcp.tool()
    def hubspot_search_meetings(
        start_date: str = "",
        end_date: str = "",
        owner: str = "",
        outcome: str = "",
        limit: int = 50,
    ) -> str:
        """Search HubSpot meetings within a date range, optionally by owner/outcome.

        Args:
            start_date: ISO date >= (default: 7 days ago)
            end_date: ISO date <= (default: today)
            owner: HubSpot owner ID filter
            outcome: hs_meeting_outcome filter (e.g. "COMPLETED", "NO_SHOW")
            limit: Max meetings (default: 50)
        """
        try:
            from mcp_server.clients import hubspot

            start, end = parse_dates(start_date, end_date, default_days=7)
            filters = [
                {"propertyName": "hs_timestamp", "operator": "GTE", "value": start.isoformat()},
                {"propertyName": "hs_timestamp", "operator": "LTE", "value": end.isoformat()},
            ]
            if owner:
                filters.append({"propertyName": "hubspot_owner_id", "operator": "EQ", "value": owner})
            if outcome:
                filters.append({"propertyName": "hs_meeting_outcome", "operator": "EQ", "value": outcome})
            props = ["hs_timestamp", "hs_meeting_title", "hs_meeting_outcome", "hubspot_owner_id"]
            rows = hubspot.search_meetings(
                [{"filters": filters}], props, limit=limit, sort_by="hs_timestamp",
            )
            return ok({"period": f"{start} to {end}", "meeting_count": len(rows), "meetings": rows})
        except Exception as ex:
            return err("hubspot_search_meetings", ex)

    @mcp.tool()
    def hubspot_contact_form_submissions(contact_id: str, limit: int = 50) -> str:
        """Form submission events for a HubSpot contact (READ-ONLY)."""
        try:
            from mcp_server.clients import hubspot
            events = hubspot.get_contact_form_submissions(contact_id, limit=limit)
            return ok({"contact_id": contact_id, "submission_count": len(events), "submissions": events})
        except Exception as ex:
            return err("hubspot_contact_form_submissions", ex)

    @mcp.tool()
    def hubspot_contact_email_engagement(contact_id: str, limit: int = 50) -> str:
        """Email opens/clicks/sent events for a HubSpot contact (READ-ONLY)."""
        try:
            from mcp_server.clients import hubspot
            events = hubspot.get_contact_email_engagement(contact_id, limit=limit)
            return ok({"contact_id": contact_id, "event_count": len(events), "events": events})
        except Exception as ex:
            return err("hubspot_contact_email_engagement", ex)

    @mcp.tool()
    def hubspot_contact_meetings(contact_id: str, limit: int = 20) -> str:
        """Meetings associated with a HubSpot contact (READ-ONLY)."""
        try:
            from mcp_server.clients import hubspot
            meetings = hubspot.get_contact_meetings(contact_id, limit=limit)
            return ok({"contact_id": contact_id, "meeting_count": len(meetings), "meetings": meetings})
        except Exception as ex:
            return err("hubspot_contact_meetings", ex)

    @mcp.tool()
    def hubspot_deal_activity_timeline(deal_id: str, limit: int = 25) -> str:
        """Notes, meetings, and calls associated with a HubSpot deal (READ-ONLY).

        Args:
            deal_id: HubSpot deal ID
            limit: Max items per activity type (default: 25)
        """
        try:
            from mcp_server.clients import hubspot
            return ok(hubspot.get_deal_activity_timeline(deal_id, limit=limit))
        except Exception as ex:
            return err("hubspot_deal_activity_timeline", ex)

    @mcp.tool()
    def hubspot_search_pipeline_summary(
        start_date: str = "",
        end_date: str = "",
        group_by: str = "dealstage",
        pipeline: str = "",
        limit: int = 200,
    ) -> str:
        """Aggregate deals by a property over a date range (count + amount sum).

        Args:
            start_date: ISO date >= createdate (default: 30 days ago)
            end_date: ISO date <= createdate (default: today)
            group_by: Deal property to group by (default: "dealstage")
            pipeline: Pipeline ID filter (optional)
            limit: Max deals to scan (default: 200)
        """
        try:
            from mcp_server.clients import hubspot

            start, end = parse_dates(start_date, end_date, default_days=30)
            filters = [
                {"propertyName": "createdate", "operator": "GTE", "value": start.isoformat()},
                {"propertyName": "createdate", "operator": "LTE", "value": end.isoformat()},
            ]
            if pipeline:
                filters.append({"propertyName": "pipeline", "operator": "EQ", "value": pipeline})
            buckets = hubspot.get_pipeline_summary([{"filters": filters}], group_by, limit=limit)
            total_amount = sum(b["amount_sum"] for b in buckets)
            total_deals = sum(b["deal_count"] for b in buckets)
            return ok({
                "period": f"{start} to {end}",
                "group_by": group_by,
                "total_deals": total_deals,
                "total_amount": round(total_amount, 2),
                "buckets": buckets,
            })
        except Exception as ex:
            return err("hubspot_search_pipeline_summary", ex)

    @mcp.tool()
    def hubspot_field_coverage(
        object_type: str = "deals",
        properties: str = "amount,closedate,dealstage,primary_source",
        sample_size: int = 200,
    ) -> str:
        """% of recent records that have each property populated.

        Args:
            object_type: "deals", "contacts", or "companies" (default: "deals")
            properties: Comma-separated properties to check
            sample_size: Recent records to sample (default: 200)
        """
        try:
            from mcp_server.clients import hubspot
            props_list = [p.strip() for p in properties.split(",")]
            return ok(hubspot.get_field_coverage(object_type, props_list, sample_size=sample_size))
        except Exception as ex:
            return err("hubspot_field_coverage", ex)

    @mcp.tool()
    def hubspot_property_distribution(
        object_type: str,
        property_name: str,
        sample_size: int = 500,
    ) -> str:
        """Value counts for a property over recent records.

        Args:
            object_type: "deals", "contacts", or "companies"
            property_name: Property to tally
            sample_size: Recent records to sample (default: 500)
        """
        try:
            from mcp_server.clients import hubspot
            return ok(hubspot.get_property_distribution(object_type, property_name, sample_size=sample_size))
        except Exception as ex:
            return err("hubspot_property_distribution", ex)

    @mcp.tool()
    def hubspot_pages_to_deals(
        url_pattern: str,
        start_date: str = "",
        end_date: str = "",
        limit: int = 100,
    ) -> str:
        """Find contacts whose first/last analytics URL contains a pattern, plus their deals.

        Args:
            url_pattern: URL substring (e.g. "/alternatives/chargebee")
            start_date: ISO date >= createdate (optional)
            end_date: ISO date <= createdate (optional)
            limit: Max contacts (default: 100)
        """
        try:
            from mcp_server.clients import hubspot
            rows = hubspot.get_pages_to_deals(
                url_pattern,
                start_date=start_date or None,
                end_date=end_date or None,
                limit=limit,
            )
            return ok({"url_pattern": url_pattern, "contact_count": len(rows), "contacts": rows})
        except Exception as ex:
            return err("hubspot_pages_to_deals", ex)
