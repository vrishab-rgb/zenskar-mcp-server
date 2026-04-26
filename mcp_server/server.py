"""Zenskar Marketing Analytics MCP Server.

Exposes read-only tools for GSC, GA4, Google Ads, HubSpot, Bing, and the
Supabase-backed Recommendations registry.

Supports two transport modes:
- stdio (default) — for Claude Code / Claude Desktop local use
- sse — for remote deployment (Render, Railway, etc.) accessible via Claude.ai web

Set MCP_TRANSPORT=sse and PORT=8000 env vars for remote mode.

Tool definitions live in `mcp_server/tools/*_tools.py`; this module is the
thin FastMCP entrypoint.
"""

import logging
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from mcp_server.tools import register_all

logging.basicConfig(level=logging.INFO)

_host = os.environ.get("HOST", "0.0.0.0")
_port = int(os.environ.get("PORT", "8000"))
_is_remote = os.environ.get("MCP_TRANSPORT", "stdio") != "stdio"

mcp = FastMCP(
    "Zenskar Marketing Analytics",
    host=_host,
    port=_port,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False) if _is_remote else None,
    instructions=(
        "Marketing analytics server for Zenskar. Provides read-only access to:\n"
        "- Google Search Console (organic search performance)\n"
        "- Google Analytics 4 (site engagement, traffic channels)\n"
        "- Google Ads (campaign performance, keywords, search terms)\n"
        "- HubSpot CRM (deals, contacts, companies — READ-ONLY)\n"
        "- Bing Webmaster Tools (Bing search performance)\n\n"
        "All date parameters accept YYYY-MM-DD format. Omit for last 28 days.\n"
        "HubSpot tools are strictly read-only — no data is ever modified."
    ),
)

register_all(mcp)


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
