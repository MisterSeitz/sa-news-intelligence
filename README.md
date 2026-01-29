# 🕵️ Niche Intelligence Actor

A powerful, multi-vertical intelligence scout designed to aggregate, deduplicate, and analyze global news feeds. It uses AI to identify high-impact events and syncs structured intelligence to your database.

## 🌟 Features

*   **Multi-Niche Support**: Specialized tracking for Gaming, Crypto, Tech, Nuclear Energy, VC, and more.
*   **Global Aggregation**: Single-click `"All Niches"` mode fetches and processes feeds across all verticals simultaneously.
*   **Smart Deduplication**: Checks your database before processing to skip articles that have already been ingrained, saving API costs and compute time.
*   **High-Speed Ingestion**: Uses parallel fetching to process 50+ feeds in seconds.
*   **Time-Based Filtering**: Automatically discards articles older than your specified limit (e.g., `24h`) to ensure freshness.
*   **Resilient AI Analysis**: 
    *   **Primary**: Alibaba Cloud Qwen (High Performance)
    *   **Fallback**: OpenRouter (Google Gemini Free Tier) ensures continuity if the primary fails.
*   **Real-Time Alerts**: Integrated Discord Webhook support to ping you immediately for "High Hype" events.
*   **Dynamic Routing**: Automatically routes data to niche-specific Supabase tables (e.g., `intelligence.gaming`, `intelligence.crypto`).

## 🏗️ Architecture

1.  **Ingestion**: Fetches RSS feeds concurrently based on the `NICHE_FEED_MAP`.
2.  **Filter & Dedup**: 
    *   Discards old content (`timeLimit`).
    *   Checks Supabase for existing URLs (`check_url_exists`).
3.  **Processing**:
    *   **Scrape**: Extracts full article text.
    *   **Fallback Search**: Uses Brave Search if scraping fails.
    *   **Analyze**: LLM extracts Sentiment, Category, Entities, and Location.
4.  **Storage & Sync**: 
    *   Pushes to Apify Dataset.
    *   Syncs to specific Supabase table (`intelligence.<niche>`).
5.  **Notification**: Sends Discord alert if sentiment is "High Hype".

## 🛠️ Configuration

### Environment Variables (Secrets)
| Variable | Description | Required |
| :--- | :--- | :--- |
| `ALIBABA_CLOUD_API_KEY` | Primary LLM Provider (Qwen) | Yes |
| `OPENROUTER_API_KEY` | Fallback LLM Provider (Gemini Free) | Yes |
| `BRAVE_API_KEY` | Search Fallback for scraping | Optional |
| `SUPABASE_URL` | Database URL | Yes |
| `SUPABASE_KEY` | Service Role Key | Yes |

### Input Parameters
| Parameter | Description | Default |
| :--- | :--- | :--- |
| `niche` | Specific vertical (`gaming`, `crypto`) or `all` for global run. | `gaming` |
| `source` | `all` for curated feeds, or `custom` for a specific URL. | `all` |
| `timeLimit` | Max age of articles to process (`24h`, `48h`, `1w`). | `w` |
| `discordWebhookUrl` | URL for "High Hype" alerts. | `null` |
| `runTestMode` | If true, uses dummy data and mocks APIs (Zero Cost). | `false` |

## 🚀 Usage

### Global Update (Production)
Run this daily to keep all intelligence tables fresh.
```json
{
  "niche": "all",
  "source": "all",
  "maxArticles": 50,
  "timeLimit": "24h",
  "discordWebhookUrl": "https://discord.com/api/webhooks/..."
}
```

### Targeted Scout
Run this to deep-dive into a specific sector.
```json
{
  "niche": "nuclear",
  "source": "all",
  "maxArticles": 20,
  "timeLimit": "1w"
}
```