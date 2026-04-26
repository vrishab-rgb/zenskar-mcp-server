"""Google Ads tools."""

from mcp_server.tools._shared import err, ok, parse_dates


def register(mcp) -> None:
    @mcp.tool()
    def ads_campaigns(start_date: str = "", end_date: str = "") -> str:
        """Get Google Ads campaign performance (cost, clicks, conversions, impression share).

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
        """
        try:
            from mcp_server.clients import google_ads

            start, end = parse_dates(start_date, end_date)
            rows = google_ads.fetch_campaigns(start, end)
            return ok({"period": f"{start} to {end}", "campaigns": rows})
        except Exception as ex:
            return err("ads_campaigns", ex)

    @mcp.tool()
    def ads_keywords(
        start_date: str = "", end_date: str = "", limit: int = 30
    ) -> str:
        """Get Google Ads keyword performance with quality scores.

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            limit: Max keywords to return (default: 30)
        """
        try:
            from mcp_server.clients import google_ads

            start, end = parse_dates(start_date, end_date)
            rows = google_ads.fetch_keywords(start, end, limit=limit)
            return ok({"period": f"{start} to {end}", "keyword_count": len(rows), "keywords": rows})
        except Exception as ex:
            return err("ads_keywords", ex)

    @mcp.tool()
    def ads_search_terms(
        start_date: str = "", end_date: str = "", limit: int = 50
    ) -> str:
        """Get actual search terms triggering Google Ads.

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            limit: Max search terms to return (default: 50)
        """
        try:
            from mcp_server.clients import google_ads

            start, end = parse_dates(start_date, end_date)
            rows = google_ads.fetch_search_terms(start, end, limit=limit)
            return ok({"period": f"{start} to {end}", "term_count": len(rows), "search_terms": rows})
        except Exception as ex:
            return err("ads_search_terms", ex)
