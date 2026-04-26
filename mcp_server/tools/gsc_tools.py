"""Google Search Console tools."""

from datetime import date

from mcp_server.tools._shared import err, ok, parse_dates


def register(mcp) -> None:
    @mcp.tool()
    def gsc_search_analytics(
        dimensions: str = "query",
        start_date: str = "",
        end_date: str = "",
        row_limit: int = 100,
        country: str = "",
    ) -> str:
        """Get Google Search Console search analytics data.

        Args:
            dimensions: Comma-separated dimensions (query, page, date, device, country). Default: "query"
            start_date: Start date YYYY-MM-DD (default: 31 days ago)
            end_date: End date YYYY-MM-DD (default: 3 days ago, due to GSC data lag)
            row_limit: Max rows to return (default: 100)
            country: 3-letter country code filter (e.g. usa, gbr, can). Empty for global.
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            dims = [d.strip() for d in dimensions.split(",")]

            filters = None
            if country:
                filters = [{"filters": [{"dimension": "country", "operator": "equals", "expression": country.lower()}]}]

            rows = gsc.fetch_search_analytics(start, end, dimensions=dims, row_limit=row_limit, dimension_filter_groups=filters)
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("gsc_search_analytics", ex)

    @mcp.tool()
    def gsc_totals(start_date: str = "", end_date: str = "") -> str:
        """Get aggregate Google Search Console totals (clicks, impressions, CTR, position).

        Args:
            start_date: Start date YYYY-MM-DD (default: 31 days ago)
            end_date: End date YYYY-MM-DD (default: 3 days ago)
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            result = gsc.fetch_totals(start, end)
            result["period"] = f"{start} to {end}"
            return ok(result)
        except Exception as ex:
            return err("gsc_totals", ex)

    @mcp.tool()
    def gsc_compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        dimensions: str = "query",
        row_limit: int = 50,
    ) -> str:
        """Compare two date periods in Google Search Console side-by-side.

        Args:
            period1_start: First period start YYYY-MM-DD
            period1_end: First period end YYYY-MM-DD
            period2_start: Second period start YYYY-MM-DD
            period2_end: Second period end YYYY-MM-DD
            dimensions: Comma-separated dimensions (default: "query")
            row_limit: Max rows per period (default: 50)
        """
        try:
            from mcp_server.clients import gsc

            p1_start = date.fromisoformat(period1_start)
            p1_end = date.fromisoformat(period1_end)
            p2_start = date.fromisoformat(period2_start)
            p2_end = date.fromisoformat(period2_end)
            dims = [d.strip() for d in dimensions.split(",")]

            p1_rows = gsc.fetch_search_analytics(p1_start, p1_end, dimensions=dims, row_limit=row_limit)
            p2_rows = gsc.fetch_search_analytics(p2_start, p2_end, dimensions=dims, row_limit=row_limit)

            dim_key = dims[0]
            p1_map = {r[dim_key]: r for r in p1_rows}
            p2_map = {r[dim_key]: r for r in p2_rows}

            all_keys = set(p1_map.keys()) | set(p2_map.keys())
            compared = []
            for key in all_keys:
                r1 = p1_map.get(key, {})
                r2 = p2_map.get(key, {})
                entry = {dim_key: key}
                for metric in ("clicks", "impressions", "ctr", "position"):
                    v1 = r1.get(metric, 0)
                    v2 = r2.get(metric, 0)
                    entry[f"p1_{metric}"] = v1
                    entry[f"p2_{metric}"] = v2
                    entry[f"{metric}_change"] = round(v2 - v1, 4)
                    if v1:
                        entry[f"{metric}_change_pct"] = round((v2 - v1) / v1 * 100, 1)
                compared.append(entry)

            compared.sort(key=lambda x: abs(x.get("clicks_change", 0)), reverse=True)

            return ok({
                "period1": f"{p1_start} to {p1_end}",
                "period2": f"{p2_start} to {p2_end}",
                "row_count": len(compared),
                "rows": compared[:row_limit],
            })
        except Exception as ex:
            return err("gsc_compare_periods", ex)
