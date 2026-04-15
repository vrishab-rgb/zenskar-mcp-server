# Zenskar Marketing Analytics — MCP Server

19-tool MCP server providing **read-only** access to Zenskar's marketing analytics stack:

| Platform | Tools | What you get |
|----------|-------|-------------|
| **Google Search Console** | 3 | Queries, pages, CTR, position, period comparison |
| **Google Analytics 4** | 4 | Engagement, channels, landing pages, custom reports |
| **Google Ads** | 3 | Campaigns, keywords with quality scores, search terms |
| **HubSpot CRM** | 7 | Deals, companies, contacts, activity, page visit journeys |
| **Bing Webmaster** | 2 | Search queries, top pages (US) |

Works with **Claude.ai web** (via Render), **Claude Desktop**, and **Claude Code**.

---

## Quick Start: Deploy to Render (free) → use from Claude.ai

### 1. Fork/clone this repo

### 2. Deploy on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service** → connect this repo
2. Render auto-detects `render.yaml`
3. Add these **environment variables** (mark as Secret):

| Variable | Value |
|----------|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Paste the full `credentials.json` content |
| `GA4_PROPERTY_ID` | `428507848` |
| `ADS_CUSTOMER_ID` | `5860587550` |
| `ADS_DEV_TOKEN` | Google Ads developer token |
| `ADS_TOKEN_JSON` | Paste the full `google_ads_token.json` content |
| `HUBSPOT_PAT` | HubSpot Personal Access Token |
| `BING_API_KEY` | Bing Webmaster Tools API key |

4. Deploy → you get a URL like `https://zenskar-mcp.onrender.com`

### 3. Add to Claude.ai

1. Go to [claude.ai](https://claude.ai) → **Settings** → **Integrations**
2. Add your Render URL: `https://zenskar-mcp.onrender.com/sse`
3. Your whole team can now use all 19 tools from any conversation

> **Note:** Render free tier sleeps after 15 min idle. First request after sleep takes ~30s. After that, instant.

---

## Alternative: Claude Desktop (local)

```bash
git clone https://github.com/vrishab-rgb/zenskar-mcp-server.git
cd zenskar-mcp-server
pip install -e .
cp .env.example .env   # fill in your credentials
```

Add to Claude Desktop config:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zenskar-marketing": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "C:\\path\\to\\zenskar-mcp-server",
      "env": {
        "DOTENV_PATH": "C:\\path\\to\\zenskar-mcp-server\\.env"
      }
    }
  }
}
```

---

## Alternative: Claude Code (local)

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "zenskar-marketing": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "C:\\path\\to\\zenskar-mcp-server",
      "env": {
        "DOTENV_PATH": "C:\\path\\to\\zenskar-mcp-server\\.env"
      }
    }
  }
}
```

---

## All 19 Tools

### Google Search Console
| Tool | Description |
|------|-------------|
| `gsc_search_analytics` | Search analytics by query/page/date/device/country |
| `gsc_totals` | Aggregate clicks, impressions, CTR, position |
| `gsc_compare_periods` | Compare two date ranges side-by-side |

### Google Analytics 4
| Tool | Description |
|------|-------------|
| `ga4_site_engagement` | Sessions, users, engagement rate, bounce rate |
| `ga4_channel_breakdown` | Traffic by channel (Organic, Paid, Direct, etc.) |
| `ga4_top_pages` | Top landing pages by sessions |
| `ga4_report` | Custom report with any GA4 metrics/dimensions |

### Google Ads
| Tool | Description |
|------|-------------|
| `ads_campaigns` | Campaign performance with cost, conversions, impression share |
| `ads_keywords` | Keyword performance with quality scores |
| `ads_search_terms` | Actual search terms triggering your ads |

### HubSpot (all read-only)
| Tool | Description |
|------|-------------|
| `hubspot_search_deals` | Search deals with filters (stage, source, date) |
| `hubspot_get_company` | Get company properties by ID |
| `hubspot_get_contact` | Get contact properties by ID |
| `hubspot_get_deal` | Get deal properties by ID |
| `hubspot_company_contacts` | Get contacts associated with a company |
| `hubspot_company_activity` | Get notes and meetings for a company |
| `hubspot_contact_journey` | Get page visit history for a contact |

### Bing Webmaster Tools
| Tool | Description |
|------|-------------|
| `bing_top_queries` | Top Bing search queries (US traffic) |
| `bing_top_pages` | Top Bing pages by clicks |

## Usage

Once connected, just ask Claude naturally:

- *"What were our top 10 GSC queries last week?"*
- *"Show me GA4 organic traffic for the US this month"*
- *"How are our Google Ads campaigns performing?"*
- *"Find all HubSpot deals created this month with source Inbound - Organic"*
- *"Get the page visit journey for contact 12345"*

All date parameters default to the last 28 days if omitted.

## Credentials

All credentials are loaded from environment variables (`.env` file locally, Render secrets for cloud). The server supports two formats for Google credentials:

- **File path**: `GOOGLE_SERVICE_ACCOUNT_JSON=credentials.json`
- **Inline JSON**: `GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}` (for cloud)

Same for Google Ads: `ADS_TOKEN_FILE` (file path) or `ADS_TOKEN_JSON` (inline).
