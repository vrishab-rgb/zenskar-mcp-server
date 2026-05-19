"""Google Docs MCP tools — create and write formatted Google Docs via service account."""

import json
import logging

from mcp_server.clients import gdocs

_log = logging.getLogger(__name__)


def register(mcp) -> None:

    @mcp.tool()
    def docs_add_tab(
        doc_id: str,
        tab_title: str,
        blocks: str,
    ) -> str:
        """
        Adds a new named tab to an existing Google Doc and writes formatted content.

        The service account must have Editor access to the target document.

        doc_id: Google Doc ID (from the URL: /document/d/<doc_id>/edit)
        tab_title: Title shown on the tab
        blocks: JSON array of content blocks. Supported types:

          {"type": "h1", "text": "Title"}
          {"type": "h2", "text": "Section"}
          {"type": "h3", "text": "Subsection"}
          {"type": "p", "text": "Body paragraph text"}
          {"type": "bullet", "text": "Bullet point text"}
          {"type": "spacer"}
          {"type": "table",
           "headers": ["Col A", "Col B", "Col C"],
           "rows": [["val1", "val2", "val3"], ...],
           "header_color": [0.18, 0.42, 0.70]}

        Returns the tab_id and a link to the document.
        """
        try:
            content = json.loads(blocks)
        except json.JSONDecodeError as e:
            return f"Error: blocks must be valid JSON — {e}"

        try:
            tab_id = gdocs.add_tab(doc_id, tab_title)
            gdocs.write_tab_content(doc_id, tab_id, content)
        except Exception as e:
            _log.exception("docs_add_tab failed")
            return f"Error: {e}"

        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return f"Tab '{tab_title}' created (tab_id={tab_id}). Document: {url}"

    @mcp.tool()
    def docs_create_doc(
        title: str,
        blocks: str,
    ) -> str:
        """
        Creates a new Google Doc owned by the service account and writes formatted content
        into its default tab.

        title: Document title
        blocks: JSON array of content blocks (same format as docs_add_tab)

        Returns the document URL.
        """
        try:
            content = json.loads(blocks)
        except json.JSONDecodeError as e:
            return f"Error: blocks must be valid JSON — {e}"

        try:
            result = gdocs.create_doc(title)
            doc_id = result["doc_id"]

            # Default tab in a new doc has a fixed tab_id; get it from the document
            svc = gdocs._get_service()
            doc = svc.documents().get(documentId=doc_id, includeTabsContent=True).execute()
            tabs = doc.get("tabs", [])
            if tabs:
                tab_id = tabs[0]["tabProperties"]["tabId"]
                gdocs.write_tab_content(doc_id, tab_id, content)
        except Exception as e:
            _log.exception("docs_create_doc failed")
            return f"Error: {e}"

        return f"Document created: {result['url']}"
