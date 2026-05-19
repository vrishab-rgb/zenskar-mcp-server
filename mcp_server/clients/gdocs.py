"""Google Docs API client — create docs and write formatted content via service account."""

import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

from mcp_server import config

_log = logging.getLogger(__name__)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
_service = None


def _get_service():
    global _service
    if _service is None:
        creds = service_account.Credentials.from_service_account_file(
            config.SERVICE_ACCOUNT_PATH, scopes=_SCOPES
        )
        _service = build("docs", "v1", credentials=creds)
    return _service


def create_doc(title: str) -> dict:
    """Creates a new Google Doc owned by the service account. Returns {doc_id, url}."""
    svc = _get_service()
    doc = svc.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    return {"doc_id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}


def add_tab(doc_id: str, tab_title: str) -> str:
    """Creates a new named tab in an existing document. Returns the tab_id."""
    svc = _get_service()
    resp = svc.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"addDocumentTab": {"tabProperties": {"title": tab_title}}}]},
    ).execute()
    return resp["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]


# ── Marker used as placeholder for table positions during text-only pass ─────
_MARKER = "<<<TABLE_{n}>>>"


def _marker(n: int) -> str:
    return _MARKER.replace("{n}", str(n))


def _find_markers_in_tab(tab_body_content: list, n_tables: int) -> list[dict]:
    """
    Returns a list of {n, start, end} for each marker paragraph found in the tab body,
    where start/end are the paragraph's startIndex/endIndex.
    """
    results = {}
    for element in tab_body_content:
        para = element.get("paragraph")
        if not para:
            continue
        text = "".join(
            el.get("textRun", {}).get("content", "")
            for el in para.get("elements", [])
        )
        for n in range(n_tables):
            if _marker(n) in text:
                results[n] = {
                    "n": n,
                    "start": element["startIndex"],
                    "end": element["endIndex"],
                }
    return [results[n] for n in sorted(results)]


def write_tab_content(doc_id: str, tab_id: str, blocks: list[dict]) -> None:
    """
    Writes formatted blocks into a document tab.

    Supported block types:
      {"type": "h1"|"h2"|"h3", "text": str}
      {"type": "p", "text": str}
      {"type": "bullet", "text": str}
      {"type": "spacer"}
      {"type": "table",
       "headers": [str, ...],
       "rows": [[str, ...], ...],
       "header_color": [r, g, b]}   <- r/g/b as 0.0–1.0 floats
    """
    svc = _get_service()

    _HEADING_MAP = {"h1": "HEADING_1", "h2": "HEADING_2", "h3": "HEADING_3"}

    # ── Stage 1: insert all text + table-marker placeholders ─────────────────
    requests: list[dict] = []
    idx = 1  # fresh tab body starts at index 1
    table_blocks: list[dict] = []  # ordered list of table blocks

    def _loc(i):
        return {"index": i, "tabId": tab_id}

    def _rng(s, e):
        return {"startIndex": s, "endIndex": e, "tabId": tab_id}

    for block in blocks:
        btype = block["type"]

        if btype in _HEADING_MAP:
            text = block["text"] + "\n"
            requests.append({"insertText": {"location": _loc(idx), "text": text}})
            requests.append({
                "updateParagraphStyle": {
                    "range": _rng(idx, idx + len(text)),
                    "paragraphStyle": {"namedStyleType": _HEADING_MAP[btype]},
                    "fields": "namedStyleType",
                }
            })
            idx += len(text)

        elif btype == "p":
            text = block["text"] + "\n"
            requests.append({"insertText": {"location": _loc(idx), "text": text}})
            idx += len(text)

        elif btype == "bullet":
            text = block["text"] + "\n"
            requests.append({"insertText": {"location": _loc(idx), "text": text}})
            requests.append({
                "createParagraphBullets": {
                    "range": _rng(idx, idx + len(text)),
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            })
            idx += len(text)

        elif btype == "spacer":
            requests.append({"insertText": {"location": _loc(idx), "text": "\n"}})
            idx += 1

        elif btype == "table":
            n = len(table_blocks)
            table_blocks.append(block)
            marker_text = _marker(n) + "\n"
            requests.append({"insertText": {"location": _loc(idx), "text": marker_text}})
            idx += len(marker_text)

    if requests:
        svc.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

    if not table_blocks:
        return

    # ── Stage 2: GET doc → find marker positions → replace with real tables ──
    doc = svc.documents().get(documentId=doc_id, includeTabsContent=True).execute()

    tab_content = None
    for tab in doc.get("tabs", []):
        if tab["tabProperties"]["tabId"] == tab_id:
            tab_content = tab["documentTab"]["body"]["content"]
            break

    if not tab_content:
        _log.warning("Tab %s not found in document after text insertion", tab_id)
        return

    markers = _find_markers_in_tab(tab_content, len(table_blocks))
    if not markers:
        _log.warning("No table markers found in tab %s", tab_id)
        return

    # Replace markers with tables — process in reverse order to preserve lower indices
    replace_requests: list[dict] = []
    for m in reversed(markers):
        n = m["n"]
        block = table_blocks[n]
        n_rows = 1 + len(block.get("rows", []))
        n_cols = len(block.get("headers", []))
        marker_start = m["start"]
        marker_end = m["end"]

        # Delete the marker paragraph content (keep the trailing \n as paragraph separator)
        # deleteContentRange removes chars [start, end)
        # The marker paragraph: startIndex=marker_start, endIndex=marker_end
        # We delete just the text content, leaving the paragraph mark
        replace_requests.append({
            "deleteContentRange": {
                "range": _rng(marker_start, marker_end - 1),  # keep the final \n
            }
        })
        # Insert table at the now-empty paragraph position
        replace_requests.append({
            "insertTable": {
                "location": _loc(marker_start),
                "rows": n_rows,
                "columns": n_cols,
            }
        })

    svc.documents().batchUpdate(
        documentId=doc_id, body={"requests": replace_requests}
    ).execute()

    # ── Stage 3: GET doc → fill cells ────────────────────────────────────────
    doc2 = svc.documents().get(documentId=doc_id, includeTabsContent=True).execute()

    tab_content2 = None
    for tab in doc2.get("tabs", []):
        if tab["tabProperties"]["tabId"] == tab_id:
            tab_content2 = tab["documentTab"]["body"]["content"]
            break

    if not tab_content2:
        return

    doc_tables = [el for el in tab_content2 if "table" in el]
    fill_requests: list[dict] = []

    # Fill tables in reverse order to avoid index drift
    for t_order in reversed(range(len(markers))):
        if t_order >= len(doc_tables):
            continue

        doc_table_el = doc_tables[t_order]
        table_start_idx = doc_table_el["startIndex"]
        block = table_blocks[t_order]
        headers = block.get("headers", [])
        data_rows = block.get("rows", [])
        hc = block.get("header_color", [0.18, 0.42, 0.70])
        all_row_data = [headers] + data_rows
        table_rows = doc_table_el["table"]["tableRows"]

        # Fill rows + cells in reverse order
        for r_idx in reversed(range(len(table_rows))):
            if r_idx >= len(all_row_data):
                continue
            row_data = all_row_data[r_idx]
            cells = table_rows[r_idx].get("tableCells", [])

            for c_idx in reversed(range(len(cells))):
                if c_idx >= len(row_data):
                    continue

                cell = cells[c_idx]
                cell_para_start = cell["content"][0]["startIndex"]
                cell_text = str(row_data[c_idx])

                fill_requests.append({
                    "insertText": {
                        "location": _loc(cell_para_start),
                        "text": cell_text,
                    }
                })

                if r_idx == 0:
                    # Header row: bold white text
                    fill_requests.append({
                        "updateTextStyle": {
                            "range": _rng(cell_para_start, cell_para_start + len(cell_text)),
                            "textStyle": {
                                "bold": True,
                                "foregroundColor": {
                                    "color": {"rgbColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                                },
                            },
                            "fields": "bold,foregroundColor",
                        }
                    })
                    # Header cell background
                    fill_requests.append({
                        "updateTableCellStyle": {
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": _loc(table_start_idx),
                                    "rowIndex": r_idx,
                                    "columnIndex": c_idx,
                                },
                                "rowSpan": 1,
                                "columnSpan": 1,
                            },
                            "tableCellStyle": {
                                "backgroundColor": {
                                    "color": {"rgbColor": {"red": hc[0], "green": hc[1], "blue": hc[2]}}
                                }
                            },
                            "fields": "backgroundColor",
                        }
                    })

    if fill_requests:
        svc.documents().batchUpdate(
            documentId=doc_id, body={"requests": fill_requests}
        ).execute()
