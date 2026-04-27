"""Google Analytics 4 tools."""

from datetime import date

from mcp_server.tools._shared import err, ok, parse_dates, period_compare


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

    @mcp.tool()
    def ga4_landing_pages_by_source(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
        limit: int = 50,
    ) -> str:
        """Top landing pages broken out by sessionSource.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Full country name filter (e.g. "United States")
            channel: Channel filter (e.g. "Organic Search")
            limit: Max rows (default: 50)
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            rows = ga4.fetch_pages_by_dimension(
                start, end, extra_dim="sessionSource",
                country=country, channel=channel, limit=limit,
            )
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_landing_pages_by_source", ex)

    @mcp.tool()
    def ga4_conversions_by_page(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
        limit: int = 50,
    ) -> str:
        """Top landing pages by key events / conversions.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Full country name filter
            channel: Channel filter
            limit: Max rows (default: 50)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            start, end = parse_dates(start_date, end_date)
            dim_filter = ga4._build_filter(country, channel)
            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "keyEvents", "engagementRate"],
                dimensions=["landingPagePlusQueryString"],
                dimension_filter=dim_filter,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="keyEvents"), desc=True)],
                limit=limit,
            )
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_conversions_by_page", ex)

    @mcp.tool()
    def ga4_compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        dimension: str = "landingPagePlusQueryString",
        country: str = "",
        channel: str = "",
        limit: int = 50,
    ) -> str:
        """Compare two date periods in GA4 side-by-side over one dimension.

        Args:
            period1_start: First period start YYYY-MM-DD
            period1_end: First period end YYYY-MM-DD
            period2_start: Second period start YYYY-MM-DD
            period2_end: Second period end YYYY-MM-DD
            dimension: Dimension to group by (default: "landingPagePlusQueryString")
            country: Country filter
            channel: Channel filter
            limit: Max rows in diff (default: 50)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            p1s = date.fromisoformat(period1_start)
            p1e = date.fromisoformat(period1_end)
            p2s = date.fromisoformat(period2_start)
            p2e = date.fromisoformat(period2_end)
            dim_filter = ga4._build_filter(country, channel)

            def fetch(s, e):
                return ga4.run_report(
                    s, e,
                    metrics=["sessions", "totalUsers", "engagementRate", "keyEvents"],
                    dimensions=[dimension],
                    dimension_filter=dim_filter,
                    order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                    limit=1000,
                )

            rows = period_compare(
                fetch, p1s, p1e, p2s, p2e,
                key_field=dimension,
                metrics=("sessions", "totalUsers", "engagementRate", "keyEvents"),
                sort_by="sessions_change",
                limit=limit,
            )
            return ok({
                "period1": f"{p1s} to {p1e}",
                "period2": f"{p2s} to {p2e}",
                "row_count": len(rows),
                "rows": rows,
            })
        except Exception as ex:
            return err("ga4_compare_periods", ex)

    @mcp.tool()
    def ga4_traffic_by_country(
        start_date: str = "",
        end_date: str = "",
        channel: str = "",
        limit: int = 30,
    ) -> str:
        """Sessions / users / engagement rate broken out by country.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            channel: Channel filter (e.g. "Organic Search")
            limit: Max countries (default: 30)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            start, end = parse_dates(start_date, end_date)
            dim_filter = ga4._build_filter("", channel)
            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "engagementRate", "keyEvents"],
                dimensions=["country"],
                dimension_filter=dim_filter,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=limit,
            )
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_traffic_by_country", ex)

    @mcp.tool()
    def ga4_user_journey(
        client_id: str,
        start_date: str = "",
        end_date: str = "",
        limit: int = 100,
    ) -> str:
        """Best-effort event timeline for a single user. Requires user-scoped clientId
        custom dimension exposed via GA4 — falls back to empty rows if not configured.

        Args:
            client_id: GA4 clientId value to filter on
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            limit: Max events (default: 100)
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            try:
                cid_filter = ga4._string_filter("clientId", client_id)
                rows = ga4.run_report(
                    start, end,
                    metrics=["eventCount"],
                    dimensions=["dateHourMinute", "eventName", "pageLocation"],
                    dimension_filter=cid_filter,
                    limit=limit,
                )
            except Exception as inner:
                return ok({
                    "period": f"{start} to {end}",
                    "client_id": client_id,
                    "note": "clientId dimension not available — set up user-scoped custom dimension in GA4 to enable.",
                    "details": str(inner),
                    "rows": [],
                })
            return ok({"period": f"{start} to {end}", "client_id": client_id,
                       "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_user_journey", ex)

    @mcp.tool()
    def ga4_funnel_report(
        steps: str,
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
    ) -> str:
        """Approximate funnel: count users who fired each event in order. Returns
        per-step user counts and step-to-step conversion rates.

        Args:
            steps: Comma-separated event names in order (e.g. "page_view,form_start,form_submit")
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Country filter
            channel: Channel filter
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            event_names = [s.strip() for s in steps.split(",") if s.strip()]
            base_filter = ga4._build_filter(country, channel)
            results = []
            prev_users = None
            for ev in event_names:
                ev_filter = ga4._and_filters(base_filter, ga4._string_filter("eventName", ev))
                rows = ga4.run_report(
                    start, end,
                    metrics=["totalUsers", "eventCount"],
                    dimension_filter=ev_filter,
                    limit=1,
                )
                users = rows[0].get("totalUsers", 0) if rows else 0
                events = rows[0].get("eventCount", 0) if rows else 0
                step_pct = round(users / prev_users * 100, 1) if prev_users else 100.0
                results.append({
                    "step": ev, "users": users, "events": events,
                    "conversion_from_prev_pct": step_pct,
                })
                prev_users = users if users else prev_users
            return ok({"period": f"{start} to {end}", "steps": results})
        except Exception as ex:
            return err("ga4_funnel_report", ex)

    @mcp.tool()
    def ga4_returning_vs_new(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
    ) -> str:
        """Split sessions/users into new vs returning.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Country filter
            channel: Channel filter
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            dim_filter = ga4._build_filter(country, channel)
            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "engagementRate", "keyEvents"],
                dimensions=["newVsReturning"],
                dimension_filter=dim_filter,
                limit=10,
            )
            return ok({"period": f"{start} to {end}", "rows": rows})
        except Exception as ex:
            return err("ga4_returning_vs_new", ex)

    @mcp.tool()
    def ga4_event_breakdown(
        event_name: str,
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
        group_by: str = "landingPagePlusQueryString",
        limit: int = 50,
    ) -> str:
        """Breakdown of a specific event by a chosen dimension (default: landing page).

        Args:
            event_name: GA4 event name (e.g. "form_submit")
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Country filter
            channel: Channel filter
            group_by: Dimension to break out (default: "landingPagePlusQueryString")
            limit: Max rows (default: 50)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            start, end = parse_dates(start_date, end_date)
            base = ga4._build_filter(country, channel)
            ev = ga4._string_filter("eventName", event_name)
            combined = ga4._and_filters(base, ev)
            rows = ga4.run_report(
                start, end,
                metrics=["eventCount", "totalUsers"],
                dimensions=[group_by],
                dimension_filter=combined,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
                limit=limit,
            )
            return ok({"event": event_name, "period": f"{start} to {end}",
                       "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_event_breakdown", ex)

    @mcp.tool()
    def ga4_traffic_by_device(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        channel: str = "",
    ) -> str:
        """Sessions / users / engagement broken out by device category.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Country filter
            channel: Channel filter
        """
        try:
            from mcp_server.clients import ga4

            start, end = parse_dates(start_date, end_date)
            dim_filter = ga4._build_filter(country, channel)
            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "engagementRate", "keyEvents", "bounceRate"],
                dimensions=["deviceCategory"],
                dimension_filter=dim_filter,
                limit=10,
            )
            return ok({"period": f"{start} to {end}", "rows": rows})
        except Exception as ex:
            return err("ga4_traffic_by_device", ex)

    @mcp.tool()
    def ga4_referrer_breakdown(
        start_date: str = "",
        end_date: str = "",
        country: str = "",
        limit: int = 30,
    ) -> str:
        """Top referrers (sessionSource) excluding direct.

        Args:
            start_date: YYYY-MM-DD (default: 28 days ago)
            end_date: YYYY-MM-DD (default: today)
            country: Country filter
            limit: Max referrers (default: 30)
        """
        try:
            from mcp_server.clients import ga4
            from google.analytics.data_v1beta.types import OrderBy

            start, end = parse_dates(start_date, end_date)
            dim_filter = ga4._build_filter(country, "")
            rows = ga4.run_report(
                start, end,
                metrics=["sessions", "totalUsers", "engagementRate", "keyEvents"],
                dimensions=["sessionSource", "sessionMedium"],
                dimension_filter=dim_filter,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                limit=limit,
            )
            return ok({"period": f"{start} to {end}", "row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("ga4_referrer_breakdown", ex)
