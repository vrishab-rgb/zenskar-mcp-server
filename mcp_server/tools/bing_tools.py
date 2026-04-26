"""Bing Webmaster Tools."""

from mcp_server.tools._shared import err, ok, parse_dates


def register(mcp) -> None:
    @mcp.tool()
    def bing_top_queries(start_date: str = "", end_date: str = "") -> str:
        """Get top Bing search queries (US traffic) with clicks, impressions, CTR, position.

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
        """
        try:
            from mcp_server.clients import bing

            start, end = parse_dates(start_date, end_date)
            rows = bing.fetch_bing_top_queries(start, end)
            return ok({"period": f"{start} to {end}", "query_count": len(rows), "queries": rows})
        except Exception as ex:
            return err("bing_top_queries", ex)

    @mcp.tool()
    def bing_top_pages(start_date: str = "", end_date: str = "") -> str:
        """Get top Bing pages by clicks (US traffic).

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
        """
        try:
            from mcp_server.clients import bing

            start, end = parse_dates(start_date, end_date)
            rows = bing.fetch_bing_top_pages(start, end)
            return ok({"period": f"{start} to {end}", "page_count": len(rows), "pages": rows})
        except Exception as ex:
            return err("bing_top_pages", ex)
