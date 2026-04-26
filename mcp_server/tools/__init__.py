"""Per-domain MCP tool registration modules.

Each `*_tools.py` exposes a `register(mcp)` function that attaches its
`@mcp.tool()` definitions to the shared FastMCP instance. The single entry
point `register_all(mcp)` wires every module in one call.
"""

from mcp_server.tools import (
    ads_tools,
    bing_tools,
    ga4_tools,
    gsc_tools,
    hubspot_tools,
    recommendations_tools,
)


def register_all(mcp) -> None:
    gsc_tools.register(mcp)
    ga4_tools.register(mcp)
    ads_tools.register(mcp)
    hubspot_tools.register(mcp)
    bing_tools.register(mcp)
    recommendations_tools.register(mcp)
