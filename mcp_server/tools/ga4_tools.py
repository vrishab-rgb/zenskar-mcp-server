"""Google Analytics 4 tools."""

from mcp_server.tools._shared import err, ok, parse_dates


def register(mcp) -> None:
    @mcp.tool()
    def ga4_site_engagement(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
    ) -> str:
        """Get GA4 site engagement metrics (sessions, users, engagement rate, bounce rate).

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            country: Full country name filter (e.g. "United States", "United Kingdom")
            channel: Channel filter (e.g. "Organic Search", "Paid Search", "Direct")
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            result = ga4.fetch_site_engagement(start, end, country=country, channel=channel)
            result["period"] = f"{start} to {end}"
            if country:
                result["country_filter"] = country
            if channel:
                result["channel_filter"] = channel
            return ok(result)
        except Exception as ex:
            return err("ga4_site_engagement", ex)

    @mcp.tool()
    def ga4_channel_breakdown(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
    ) -> str:
        """Get GA4 traffic breakdown by channel (Organic Search, Paid Search, Direct, etc.).

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            country: Full country name filter (e.g. "United States")
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            rows = ga4.fetch_channel_breakdown(start, end, country=country)
            return ok({"period": f"{start} to {end}", "channels": rows})
        except Exception as ex:
            return err("ga4_channel_breakdown", ex)

    @mcp.tool()
    def ga4_top_pages(
        start_date: str = "",
        end_date: str = "",
        limit: int = 30,
        country: str = "",
        channel: str = "",
    ) -> str:
        """Get top landing pages by sessions from GA4.

        Args:
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            limit: Max pages to return (default: 30)
            country: Full country name filter (e.g. "United States")
            channel: Channel filter (e.g. "Organic Search")
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            rows = ga4.fetch_top_pages(start, end, limit=limit, country=country, channel=channel)
            return ok({"period": f"{start} to {end}", "page_count": len(rows), "pages": rows})
        except Exception as ex:
            return err("ga4_top_pages", ex)

    @mcp.tool()
    def ga4_report(
        metrics: str,
        dimensions: str = "",
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
        limit: int = 50,
    ) -> str:
        """Run a custom GA4 report with any metrics and dimensions.

        Args:
            metrics: Comma-separated metric names (e.g. "sessions,totalUsers,keyEvents")
            dimensions: Comma-separated dimension names (e.g. "date,country"). Optional.
            start_date: Start date YYYY-MM-DD (default: 28 days ago)
            end_date: End date YYYY-MM-DD (default: today)
            country: Full country name filter
            channel: Channel filter
            limit: Max rows (default: 50)
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            metrics_list = [m.strip() for m in metrics.split(",")]
            dims_list = [d.strip() for d in dimensions.split(",") if d.strip()] or None
            dim_filter = ga4._build_filter(country, channel)

            from google.analytics.data_v1beta.types import OrderBy

            order = None
            if dims_list:
                order = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metrics_list[0]), desc=True)]

            rows = ga4.run_report(
                start, end,
                metrics=metrics_list,
                dimensions=dims_list,
                dimension_filter=dim_filter,
                order_by=order,
                limit=limit,
            )
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_report", ex)
