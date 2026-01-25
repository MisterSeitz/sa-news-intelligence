# 🇿🇦 SA News & Crime Intelligence System

This system is a sophisticated **Intelligence Gathering Actor** designed to monitor, analyze, and structure open-source data related to crime, civil unrest, and major events in South Africa. It prioritizes actionable intelligence, deep entity extraction, and real-time alerting.

---

## 🏗️ System Architecture

The system operates as a modular pipeline, transforming unstructured web data into high-fidelity intelligence.

### 1. Core Components

*   **`main.py` (Controller)**: The entry point. It parses input, initializes components, and routes execution to either the General News Scraper or the specialized `CrimeIntelligenceEngine`.
*   **`CrimeIntelligenceEngine` (Orchestrator)**: The brain of the crime monitoring module.
    *   **Search**: Uses **Brave Search API** with a 3-tier key rotation strategy (Free Search -> Free AI -> Paid Base) to minimize costs.
    *   **Targeting**: Iterates through South African major metros and high-risk zones.
*   **`NewsScraper` (Gatherer)**: A robust `httpx` and `BeautifulSoup` based scraper. It handles smart user-agent rotation, content extraction, and now includes **Deep Crawling** capabilities to traverse archive pages.
*   **`IntelligenceExtractor` (Analyst)**: The AI layer.
    *   **Stage 1 (Snippet Analysis)**: Rapidly evaluates search result snippets to filter out irrelevant noise (e.g., "crime novels", "video games").
    *   **Stage 2 (Deep Intelligence)**: Performs comprehensive analysis on full article text to extract incidents, syndicates, and detailed suspect profiles.
*   **`SupabaseIngestor` (Load)**: Handles transactional data ingestion into Supabase, managing deduplication (MD5 hashes), foreign key resolution, and raw data archival.

### 2. Data Flow: The Deep Intelligence Pipeline

1.  **Scanning**: The `CrimeEngine` queries Brave Search for real-time incidents (e.g., *"cash in transit heist Johannesburg today"*).
2.  **Filter Gate**: `analyze_crime_snippet` acts as a cost-effective gatekeeper. Only high-probability crime reports pass.
3.  **Deep Dive**: The system visits the full URL, scraping the complete text.
4.  **AI Extraction**: A specialized LLM prompt analyzes the text to extract:
    *   **Incidents**: Type, Severity (1-3), Location, Modus Operandi.
    *   **Entities**: Suspects, Victims, Officials (mapped to `people_intelligence`).
    *   **Organizations**: Gangs, Syndicates, Security Companies.
5.  **Ingestion & Alerting**:
    *   Structured data is saved to `crime_intelligence.incidents`.
    *   Full text is archived in `incidents.full_text` for future NLP.
    *   **Real-Time Webhook**: If `Severity >= 3` (High), a JSON payload is immediately POSTed to the configured `webhookUrl`.

---

## 💾 Database Schema (Supabase)

Data is normalized across several key schemas to support network analysis and complex querying.

### `crime_intelligence` Schema
| Table | Description | Key Columns |
| :--- | :--- | :--- |
| `incidents` | The central event registry. | `id`, `type`, `description`, `severity`, `location`, `full_text` |
| `syndicates` | Organized crime groups. | `name`, `modus_operandi`, `active_regions` |
| `structured_crime_intelligence` | Audit log of raw AI output. | `source_url`, `ai_analysis_json`, `model_used` |

### `people_intelligence` Schema
| Table | Description | Key Columns |
| :--- | :--- | :--- |
| `wanted_people` | Suspects and wanted persons. | `name`, `status` (Wanted/Arrested), `crimes_linked` |
| `missing_people` | Missing persons registry. | `name`, `last_seen_date`, `location` |

### `ai_intelligence` Schema
| Table | Description | Key Columns |
| :--- | :--- | :--- |
| `entries` | General news & "On This Day" history. | `title`, `summary`, `sentiment_score`, `canonical_url` |

---

## ⚙️ Configuration & Input

The actor is configured via `input.json` and environment variables.

### Environment Variables (Secrets)
*   **LLM Providers**: `OPENAI_API_KEY` (Primary), `ALIBABA_CLOUD_API_KEY` (Fallback), `OPENROUTER_API_KEY`.
*   **Search**: `BRAVE_SEARCH_API` (Required), `BRAVE_AI_API` (Optional), `BRAVE_BASE_API` (Optional).
*   **Database**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

### Input Schema (`input.json`)
```json
{
  "runMode": "crime_intelligence",   // or "news_scraper"
  "crimeCityScope": "major_cities",  // "national", "major_cities", "gauteng"
  "webhookUrl": "https://your-webhook.com/api/alerts",
  "maxArticlesPerSource": 5,
  "test_mode": false
}
```

---

## 🚀 Key Features

*   **Dual-Stage Analysis**: Cost-efficient filtering followed by deep, rich extraction.
*   **Data Permanence**: We never throw away data. Full article text and raw AI JSON are preserved for future model training or re-analysis.
*   **Resilient Scraping**: Uses `httpx` with smart headers for speed, falling back to basic extraction if needed.
*   **Operational Security**: Strict "South Africa" context limits to prevent data pollution from global events.