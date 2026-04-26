"""HubSpot CRM tools (READ-ONLY)."""

import json

from mcp_server.tools._shared import err, ok


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
