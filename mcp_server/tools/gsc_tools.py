"""Google Search Console tools."""

from datetime import date

from mcp_server.tools._shared import (
    branded_filter,
    country_filter,
    err,
    ok,
    parse_dates,
    period_compare,
)


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

    @mcp.tool()
    def gsc_query_to_pages(
        query: str,
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        row_limit: int = 50,
    ) -> str:
        """Find which pages rank for a given query in GSC.

        Args:
            query: Exact query string to filter on
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            country: 3-letter country code (e.g. "usa"); empty for global
            row_limit: Max pages (default: 50)
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            filter_groups = [{"filters": [
                {"dimension": "query", "operator": "equals", "expression": query}
            ]}]
            cf = country_filter(country)
            if cf:
                filter_groups.extend(cf)
            rows = gsc.fetch_search_analytics(
                start, end, dimensions=["page"],
                row_limit=row_limit, dimension_filter_groups=filter_groups,
            )
            return ok({"query": query, "period": f"{start} to {end}",
                       "page_count": len(rows), "pages": rows})
        except Exception as ex:
            return err("gsc_query_to_pages", ex)

    @mcp.tool()
    def gsc_position_distribution(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
    ) -> str:
        """Bucket indexed pages by average position (1-3 / 4-10 / 11-20 / 21+).

        Args:
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            country: 3-letter country code; empty for global
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            result = gsc.fetch_position_distribution(start, end, country=country)
            result["period"] = f"{start} to {end}"
            return ok(result)
        except Exception as ex:
            return err("gsc_position_distribution", ex)

    @mcp.tool()
    def gsc_page_query_matrix(
        page_url: str,
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        row_limit: int = 100,
    ) -> str:
        """Find which queries drive impressions/clicks to a specific page.

        Args:
            page_url: Full or partial page URL (uses GSC 'contains' if no protocol)
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            country: 3-letter country code; empty for global
            row_limit: Max queries (default: 100)
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            op = "equals" if page_url.startswith("http") else "contains"
            filter_groups = [{"filters": [
                {"dimension": "page", "operator": op, "expression": page_url}
            ]}]
            cf = country_filter(country)
            if cf:
                filter_groups.extend(cf)
            rows = gsc.fetch_search_analytics(
                start, end, dimensions=["query"],
                row_limit=row_limit, dimension_filter_groups=filter_groups,
            )
            return ok({"page": page_url, "period": f"{start} to {end}",
                       "query_count": len(rows), "queries": rows})
        except Exception as ex:
            return err("gsc_page_query_matrix", ex)

    @mcp.tool()
    def gsc_movers_and_losers(
        period_a_start: str,
        period_a_end: str,
        period_b_start: str,
        period_b_end: str,
        country: str = "",
        top_n: int = 25,
    ) -> str:
        """Pages whose position changed most between two periods (positive = improved).

        Args:
            period_a_start: First (older) period start YYYY-MM-DD
            period_a_end: First period end YYYY-MM-DD
            period_b_start: Second (newer) period start YYYY-MM-DD
            period_b_end: Second period end YYYY-MM-DD
            country: 3-letter country code; empty for global
            top_n: How many top movers and losers to return each (default: 25)
        """
        try:
            from mcp_server.clients import gsc

            pa_s = date.fromisoformat(period_a_start)
            pa_e = date.fromisoformat(period_a_end)
            pb_s = date.fromisoformat(period_b_start)
            pb_e = date.fromisoformat(period_b_end)

            def fetch(s, e):
                return gsc.fetch_page_metrics(s, e, country=country)

            rows = period_compare(
                fetch, pa_s, pa_e, pb_s, pb_e,
                key_field="page",
                sort_by="position_change",
                limit=10000,
            )
            # Position: lower is better, so improvement = position_change < 0
            improved = sorted(
                [r for r in rows if r.get("position_change", 0) < 0],
                key=lambda r: r["position_change"],
            )[:top_n]
            declined = sorted(
                [r for r in rows if r.get("position_change", 0) > 0],
                key=lambda r: r["position_change"], reverse=True,
            )[:top_n]
            return ok({
                "period_a": f"{pa_s} to {pa_e}",
                "period_b": f"{pb_s} to {pb_e}",
                "improved": improved,
                "declined": declined,
            })
        except Exception as ex:
            return err("gsc_movers_and_losers", ex)

    @mcp.tool()
    def gsc_zero_click_pages(
        start_date: str = "",
        end_date: str = "",
        min_impressions: int = 200,
        country: str = "",
        row_limit: int = 100,
    ) -> str:
        """Pages with high impressions but ~0 clicks (CTR opportunities).

        Args:
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            min_impressions: Minimum impressions threshold (default: 200)
            country: 3-letter country code; empty for global
            row_limit: Max pages to inspect (default: 100)
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            rows = gsc.fetch_page_metrics(start, end, country=country)
            zero_click = [
                r for r in rows
                if (r.get("impressions", 0) or 0) >= min_impressions
                and (r.get("clicks", 0) or 0) == 0
            ]
            zero_click.sort(key=lambda r: r.get("impressions", 0), reverse=True)
            return ok({
                "period": f"{start} to {end}",
                "min_impressions": min_impressions,
                "page_count": len(zero_click),
                "pages": zero_click[:row_limit],
            })
        except Exception as ex:
            return err("gsc_zero_click_pages", ex)

    @mcp.tool()
    def gsc_branded_vs_unbranded(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        brand_terms: str = "zenskar",
    ) -> str:
        """Split GSC totals into branded vs unbranded query buckets.

        Args:
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            country: 3-letter country code; empty for global
            brand_terms: Comma-separated brand regex terms (default: "zenskar")
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            terms = [t.strip() for t in brand_terms.split(",") if t.strip()]
            cf = country_filter(country) or []

            branded = gsc.fetch_search_analytics(
                start, end, dimensions=[],
                dimension_filter_groups=branded_filter(terms, included=True) + cf,
                row_limit=1,
            )
            unbranded = gsc.fetch_search_analytics(
                start, end, dimensions=[],
                dimension_filter_groups=branded_filter(terms, included=False) + cf,
                row_limit=1,
            )

            def first(rows):
                if rows:
                    return {k: rows[0].get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
                return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}

            return ok({
                "period": f"{start} to {end}",
                "brand_terms": terms,
                "branded": first(branded),
                "unbranded": first(unbranded),
            })
        except Exception as ex:
            return err("gsc_branded_vs_unbranded", ex)

    @mcp.tool()
    def gsc_country_comparison(
        start_date: str = "",
        end_date: str = "",
        countries: str = "usa,gbr,ind",
    ) -> str:
        """Compare GSC totals across multiple countries.

        Args:
            start_date: YYYY-MM-DD (default: 31 days ago)
            end_date: YYYY-MM-DD (default: 3 days ago)
            countries: Comma-separated 3-letter country codes (default: "usa,gbr,ind")
        """
        try:
            from mcp_server.clients import gsc

            start, end = parse_dates(start_date, end_date, lag_days=3)
            codes = [c.strip().lower() for c in countries.split(",") if c.strip()]
            results = []
            for code in codes:
                rows = gsc.fetch_search_analytics(
                    start, end, dimensions=[],
                    dimension_filter_groups=country_filter(code),
                    row_limit=1,
                )
                if rows:
                    entry = {k: rows[0].get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
                else:
                    entry = {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
                entry["country"] = code
                results.append(entry)
            results.sort(key=lambda r: r.get("clicks", 0), reverse=True)
            return ok({"period": f"{start} to {end}", "countries": results})
        except Exception as ex:
            return err("gsc_country_comparison", ex)
