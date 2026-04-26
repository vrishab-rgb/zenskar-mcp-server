"""Recommendation registry tools (Supabase-backed)."""

import json

from mcp_server.tools._shared import err, ok


def register(mcp) -> None:
    @mcp.tool()
    def recommendations_list(
        status: str = "",
        rec_type: str = "",
        subject_contains: str = "",
        since: str = "",
        until: str = "",
        limit: int = 50,
    ) -> str:
        """List recommendations from the registry, filtered by structured fields.

        Args:
            status: Filter by status (pending|done|abandoned|superseded). Empty for all.
            rec_type: Filter by rec type (seo|cro|paid|content|demo|ops). Empty for all.
            subject_contains: Substring match on subject (URL/query/campaign). Empty for all.
            since: Only recs raised on or after this date (YYYY-MM-DD).
            until: Only recs raised on or before this date (YYYY-MM-DD).
            limit: Max rows to return (default 50).
        """
        try:
            from mcp_server.clients import recommendations as recs

            rows = recs.list_recs(
                status=status,
                rec_type=rec_type,
                subject_contains=subject_contains,
                since=since,
                until=until,
                limit=limit,
            )
            return ok({"row_count": len(rows), "recommendations": rows})
        except Exception as ex:
            return err("recommendations_list", ex)

    @mcp.tool()
    def recommendations_get(rec_id: int) -> str:
        """Fetch a single recommendation by id.

        Args:
            rec_id: Numeric id of the recommendation.
        """
        try:
            from mcp_server.clients import recommendations as recs

            rec = recs.get_rec(rec_id)
            if rec is None:
                return ok({"error": f"No recommendation with id {rec_id}"})
            return ok(rec)
        except Exception as ex:
            return err("recommendations_get", ex)

    @mcp.tool()
    def recommendations_add(
        text: str,
        source_report: str,
        date_raised: str,
        subject: str = "",
        rec_type: str = "",
        expected_impact: str = "",
        effort: str = "",
        measurement_spec_json: str = "",
        notes: str = "",
    ) -> str:
        """Add a new recommendation to the registry.

        Args:
            text: The recommendation text (full sentence/phrase).
            source_report: Filename of the report that emitted this rec.
            date_raised: Date the rec was first raised (YYYY-MM-DD).
            subject: URL path, query string, or campaign name being acted upon.
            rec_type: One of seo|cro|paid|content|demo|ops.
            expected_impact: Free-text impact note from the report.
            effort: Free-text effort note from the report.
            measurement_spec_json: JSON string of measurement_spec, or empty for unmeasurable recs.
            notes: Any additional notes.
        """
        try:
            from mcp_server.clients import recommendations as recs

            spec = json.loads(measurement_spec_json) if measurement_spec_json else None

            fields = {
                "text": text,
                "source_report": source_report,
                "date_raised": date_raised,
                "subject": subject or None,
                "rec_type": rec_type or None,
                "expected_impact": expected_impact or None,
                "effort": effort or None,
                "measurement_spec": spec,
                "notes": notes or None,
                "status": "pending",
            }
            fields = {k: v for k, v in fields.items() if v is not None}

            rec = recs.add_rec(fields)
            return ok({"inserted": rec})
        except Exception as ex:
            return err("recommendations_add", ex)

    @mcp.tool()
    def recommendations_update(
        rec_id: int,
        status: str = "",
        outcome_json: str = "",
        done_notes: str = "",
        measurement_spec_json: str = "",
        notes: str = "",
    ) -> str:
        """Update fields on a recommendation.

        When status is set to 'done', sets done_at = now() and computes
        measure_after_date from the rec's measurement_spec (or the new spec passed in).

        Args:
            rec_id: Numeric id of the rec to update.
            status: New status (pending|done|abandoned|superseded). Empty to leave unchanged.
            outcome_json: Optional JSON outcome (overrides auto-measurement).
            done_notes: Free-text note about what shipped / why abandoned.
            measurement_spec_json: New measurement_spec (overrides existing if set).
            notes: General notes update.
        """
        try:
            from datetime import datetime, timezone

            from mcp_server.clients import recommendations as recs

            fields: dict = {}

            if status:
                fields["status"] = status
            if outcome_json:
                fields["outcome"] = json.loads(outcome_json)
            if done_notes:
                fields["done_notes"] = done_notes
            if notes:
                fields["notes"] = notes

            new_spec = None
            if measurement_spec_json:
                new_spec = json.loads(measurement_spec_json)
                fields["measurement_spec"] = new_spec

            if status == "done":
                now = datetime.now(timezone.utc)
                fields["done_at"] = now.isoformat()

                spec = new_spec
                if spec is None:
                    existing = recs.get_rec(rec_id)
                    if existing is None:
                        return err(
                            "recommendations_update",
                            ValueError(f"No rec with id {rec_id}"),
                        )
                    spec = existing.get("measurement_spec")

                mad = recs.compute_measure_after_date(now, spec)
                fields["measure_after_date"] = mad

            if not fields:
                return ok({"error": "Nothing to update — pass at least one field"})

            rec = recs.update_rec(rec_id, fields)
            return ok({"updated": rec})
        except Exception as ex:
            return err("recommendations_update", ex)

    @mcp.tool()
    def recommendations_outcomes_pending() -> str:
        """List recs that are ready for outcome measurement.

        Returns recs where status='done', outcome IS NULL, and the treatment window
        has fully ended (measure_after_date <= today).
        """
        try:
            from mcp_server.clients import recommendations as recs

            rows = recs.outcomes_pending()
            return ok({"row_count": len(rows), "recommendations": rows})
        except Exception as ex:
            return err("recommendations_outcomes_pending", ex)

    @mcp.tool()
    def recommendations_measure_outcome(rec_id: int) -> str:
        """Compute and store the outcome for a done rec by querying the relevant data source.

        Reuses the existing GSC/GA4/Ads/HubSpot client modules. Idempotent — repeat calls
        return the same outcome (modulo measured_at). Always reports n_days,
        confounders_to_consider, and uses 'observed change' phrasing rather than
        causal attribution.

        Args:
            rec_id: Numeric id of the rec to measure.
        """
        try:
            from mcp_server.clients import recommendations as recs

            rec = recs.get_rec(rec_id)
            if rec is None:
                return err(
                    "recommendations_measure_outcome",
                    ValueError(f"No rec with id {rec_id}"),
                )

            outcome = recs.compute_outcome(rec)
            return ok({"rec_id": rec_id, "outcome": outcome})
        except Exception as ex:
            return err("recommendations_measure_outcome", ex)

    @mcp.tool()
    def recommendations_query(sql: str) -> str:
        """Run a read-only SELECT (or WITH ... SELECT) against the recommendations table.

        Validation happens server-side via the exec_recommendations_select Postgres function:
        must start with SELECT or WITH; multiple statements rejected; INSERT/UPDATE/DELETE/DROP/etc.
        keywords rejected. Use for analytical questions Claude formulates on the fly.

        Args:
            sql: SELECT statement against the `recommendations` table.
        """
        try:
            from mcp_server.clients import recommendations as recs

            rows = recs.query_select(sql)
            return ok({"row_count": len(rows), "rows": rows})
        except Exception as ex:
            return err("recommendations_query", ex)
