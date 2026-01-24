# 📰 World News Intelligence Pipeline

This actor is a powerful data-gathering tool that transforms raw news from top RSS feeds (focused on **Global Affairs, Geopolitics, and Major World Events**) into structured, actionable intelligence. It uses DuckDuckGo News Search to gather real-time context and an LLM (OpenAI) to perform advanced analysis.

This actor is designed to run on a schedule, continuously gathering fresh intelligence. The structured data it produces is intended to be consumed by other systems, such as our flagship actor, **Content Blueprint AI**, which can use this stream of data to generate reports, global briefings, analysis, and more.

---

## How to Use

You have two primary ways to use this actor:

1.  **As a Data Source for Downstream Systems:** This is the primary intended use. Run this actor on a schedule to build a dataset of fresh intelligence. Other tools, including the `Content Blueprint AI` actor, can then be pointed to this actor's dataset to generate final content and reports.
2.  **As a Standalone Tool:** Run this actor to generate high-quality, structured news intelligence. You are free to download the resulting dataset for your own geopolitical analysis, risk assessment, or to feed into other custom research workflows.

---

## Features

-   **Comprehensive Source Aggregation**: Gathers news from a curated list of top-tier World News and Geopolitical feeds.
-   **Real-Time Grounding (DuckDuckGo)**: Uses the **DuckDuckGo News Search** to find fresh, corroborating snippets for each article, enriching the context before analysis. This ensures the summary is based on current, cross-validated information.
-   **Advanced AI Analysis**: Leverages an LLM to analyze each article for sentiment/impact (e.g., `High Impact`, `Developing Story`, `Informational`), categorize the topic (e.g., `Conflict/Security`, `Policy/Diplomacy`, `Social/Humanitarian`), and extract key entities.
-   **Resilient Processing**: The pipeline is designed to **fall back** to the original RSS summary if the DuckDuckGo search fails, ensuring the run completes without crashing.
-   **Duplicate Prevention**: Intelligently tracks processed articles across runs to ensure you only process and pay for new information.
-   **Cost-Saving Test Mode**: Includes a test mode to run the full workflow with dummy data, allowing for development and testing without incurring API costs.

---

## Setup and Configuration

Before running the actor, you only need to provide an API key for the LLM service.

1.  **OpenAI API Key**:
    * You will need an API key from your OpenAI account.

### Add Keys to Apify Secrets

For security, add this key as a **secret environment variable** in your Apify Actor settings:

-   `OPENAI_API_KEY`: Your OpenAI API Key.

---

## Cost of Usage 💸

**Important Note:** The costs listed below are for **this actor only**. Using this data with any other actor will incur its own separate API and platform costs.

### Costs for This Actor

1.  **Apify Platform Usage**: Standard platform costs for running the actor, which depends on the duration of the run.
2.  **DuckDuckGo Search**: This service is **free** and is handled internally by the actor, replacing the need for paid search APIs. The actor performs **one search query for every article** it processes.
3.  **OpenAI API**: This is the primary cost. The actor makes **two LLM calls for every article**: one to summarize the DuckDuckGo Search snippets and another to perform the final analysis (sentiment, category, etc.).

---

## Input

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `source` | String | `all` | The news source category to use (e.g., 'all', 'bbc-world', 'reuters-top'). |
| `customFeedUrl` | String | `null` | A custom RSS feed URL to use if `source` is set to `custom`. |
| `maxArticles` | Integer | `20` | The maximum number of new articles to fetch and process in a single run. |
| `region` | String | `wt-wt` | Region to limit search results by (e.g., 'us-en' for US, 'wt-wt' for World). |
| `timeLimit` | String | `w` | Limit search results by time (e.g., 'd' for day, 'w' for week). |
| `runTestMode` | Boolean | `false` | Bypasses all external API calls for zero-cost testing. **Do not enable in production.** |

---

## Output

The actor saves its results in the dataset. Each item is a structured JSON object with the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `source` | String | The name of the news source (e.g., 'BBC News'). |
| `title` | String | The original title of the news article. |
| `url` | String | The URL of the original article. |
| `published` | String | The publication date string from the RSS feed. |
| `summary` | String | The AI-generated summary of the article. |
| `sentiment` | String | The AI-analyzed impact level (e.g., `High Impact`, `Developing Story`, `Informational`). |
| `category` | String | The AI-assigned category (e.g., `Conflict/Security`, `Policy/Diplomacy`, `Environment`). |
| `key_entities` | Array of Strings | A list of key entities like countries, organizations, or political figures. |