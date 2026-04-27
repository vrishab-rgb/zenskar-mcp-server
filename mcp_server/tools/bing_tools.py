"""Bing Webmaster Tools."""

import re
from datetime import date

from mcp_server.tools._shared import err, ok, parse_dates, period_compare


_DEFAULT_BRAND_TERMS = ["zenskar"]


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

    @mcp.tool()
    def bing_compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        dimension: str = "query",
        limit: int = 50,
    ) -> str:
        """Compare two date periods in Bing side-by-side.

        Args:
            period1_start: First period start YYYY-MM-DD
            period1_end: First period end YYYY-MM-DD
            period2_start: Second period start YYYY-MM-DD
            period2_end: Second period end YYYY-MM-DD
            dimension: "query" or "page" (default: "query")
            limit: Max rows in diff (default: 50)
        """
        try:
            from mcp_server.clients import bing

            p1s = date.fromisoformat(period1_start)
            p1e = date.fromisoformat(period1_end)
            p2s = date.fromisoformat(period2_start)
            p2e = date.fromisoformat(period2_end)
            if dimension == "page":
                fetch = bing.fetch_bing_top_pages
                key = "page"
                metrics = ("clicks", "impressions")
            else:
                fetch = bing.fetch_bing_top_queries
                key = "query"
                metrics = ("clicks", "impressions", "ctr", "position")
            rows = period_compare(
                fetch, p1s, p1e, p2s, p2e, key_field=key,
                metrics=metrics, sort_by="clicks_change", limit=limit,
            )
            return ok({
                "period1": f"{p1s} to {p1e}",
                "period2": f"{p2s} to {p2e}",
                "row_count": len(rows), "rows": rows,
            })
        except Exception as ex:
            return err("bing_compare_periods", ex)

    @mcp.tool()
    def bing_query_to_pages(
        query: str,
        start_date: str = "",
        end_date: str = "",
        row_limit: int = 50,
    ) -> str:
        """Find which Bing pages rank for a given query.

        Args:
            query: Exact query string
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            row_limit: Max pages (default: 50)
        """
        try:
            from mcp_server.clients import bing

            start, end = parse_dates(start_date, end_date)
            rows = bing.fetch_bing_query_to_pages(query, start, end)
            return ok({"query": query, "period": f"{start} to {end}",
                       "page_count": len(rows[:row_limit]), "pages": rows[:row_limit]})
        except Exception as ex:
            return err("bing_query_to_pages", ex)

    @mcp.tool()
    def bing_page_query_matrix(
        page_url: str,
        start_date: str = "",
        end_date: str = "",
        row_limit: int = 100,
    ) -> str:
        """Find which Bing queries drive a specific page.

        Args:
            page_url: Page URL
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            row_limit: Max queries (default: 100)
        """
        try:
            from mcp_server.clients import bing

            start, end = parse_dates(start_date, end_date)
            rows = bing.fetch_bing_page_to_queries(page_url, start, end)
            return ok({"page": page_url, "period": f"{start} to {end}",
                       "query_count": len(rows[:row_limit]), "queries": rows[:row_limit]})
        except Exception as ex:
            return err("bing_page_query_matrix", ex)

    @mcp.tool()
    def bing_branded_vs_unbranded(
        start_date: str = "",
        end_date: str = "",
        brand_terms: str = "zenskar",
    ) -> str:
        """Split Bing query totals into branded vs unbranded buckets.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            brand_terms: Comma-separated brand regex terms (default: "zenskar")
        """
        try:
            from mcp_server.clients import bing

            start, end = parse_dates(start_date, end_date)
            terms = [t.strip().lower() for t in brand_terms.split(",") if t.strip()]
            pattern = re.compile("|".join(re.escape(t) for t in terms or _DEFAULT_BRAND_TERMS))

            rows = bing.fetch_bing_top_queries(start, end)
            branded = {"clicks": 0, "impressions": 0}
            unbranded = {"clicks": 0, "impressions": 0}
            for r in rows:
                bucket = branded if pattern.search((r.get("query") or "").lower()) else unbranded
                bucket["clicks"] += r.get("clicks", 0) or 0
                bucket["impressions"] += r.get("impressions", 0) or 0
            for b in (branded, unbranded):
                impr = b["impressions"]
                b["ctr"] = round(b["clicks"] / impr, 4) if impr else 0.0
            return ok({
                "period": f"{start} to {end}",
                "brand_terms": terms,
                "branded": branded,
                "unbranded": unbranded,
            })
        except Exception as ex:
            return err("bing_branded_vs_unbranded", ex)
