import feedparser
import re
from typing import List, Tuple, Dict, Any, Union
from apify import Actor
from openai import OpenAI
from openai import APIError
from langchain_community.tools import DuckDuckGoSearchResults
import json
import requests
from datetime import datetime, timedelta
from .models import Article
from collections import deque
import asyncio
import os
from urllib.parse import urlparse


# --- LLM INITIALIZATION: init_openai ---
def init_openai() -> OpenAI:
    """Initializes the OpenAI client using the OPENAI_API_KEY environment variable."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        Actor.log.error("OPENAI_API_KEY environment variable not set. Cannot initialize OpenAI client.")
        raise ValueError("OPENAI_API_KEY environment variable is missing.")
    return OpenAI(api_key=api_key)


# Global categories for the model to choose from (World News focused)
CATEGORIES = [
    "Politics/Government", "Conflict/Security", "Economy/Trade", 
    "Environment/Climate", "Health/Science", "Human Rights/Social Issues", 
    "Technology", "Disaster/Accident"
]

# Categorized Feed Map (UPDATED FOR WORLD NEWS FOCUS)
CATEGORIZED_FEEDS = {
    "Technology": [
        "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/section/technology/rss.xml",
        "https://www.bbc.co.uk/news/technology/rss.xml",
        "https://www.reuters.com/arc/outboundfeeds/technology-news/?outputType=xml",
        "https://techcrunch.com/feed/",
        "https://www.zdnet.com/topic/technology/rss.xml"
    ],
    "Business/Finance": [
        "https://www.wsj.com/xml/rss/3_7014.xml",
        "https://feeds.bloomberg.com/business/news.rss",
        "https://www.ft.com/rss/world/economy",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://hbr.org/feed"
    ],
    "World/Politics": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reuters.com/arc/outboundfeeds/world-news/?outputType=xml",
        "https://www.economist.com/latest/rss.xml",
        "https://www.politico.com/rss/politicopulse.xml"
    ],
    "Health/Science": [
        # Note: The original provided URL seems like an article, but we keep the other feeds for a valid actor.
        # "https://www.sciencedaily.com/releases/2025/10/251018102132.htm",
        "https://rss.sciencedaily.com/health_medicine.xml",
        "https://www.newscientist.com/feed/home/",
        "https://www.sciam.com/feed/rss/all/",
        "https://www.nih.gov/feed/health-topics/feed"
    ],
    "Lifestyle/Culture": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
        "https://www.theguardian.com/lifeandstyle/rss"
    ],
    "Other": [
        "https://www.axios.com/rss/feed/all",
        "https://www.npr.org/rss/rss.php?id=100",
        "https://www.theatlantic.com/feed/all/"
    ]
}

# --- RSS FETCH function (REMAINS ALMOST THE SAME, REMOVED ALPHA VANTAGE CHECK) ---
def fetch_rss_feeds(source: str, custom_url: str = None, max_articles: int = 20) -> List[Article]:
    """Fetch and parse RSS feed entries."""

    urls = []
    category_name = source
    if source == "custom" and custom_url:
        urls = [custom_url]
    elif source == "all":
        urls = list(set(url for category_list in CATEGORIZED_FEEDS.values() for url in category_list))
    elif source in CATEGORIZED_FEEDS:
        urls = CATEGORIZED_FEEDS[source]
    else:
        Actor.log.error(f"Invalid source or category selected: {source}")
        return []

    Actor.log.info(f"Fetching articles from category: {category_name} ({len(urls)} feeds)")

    parsed_feeds = []
    for feed_url in urls:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                source_title = parsed.feed.get("title", f"Unknown ({feed_url})")
                parsed_feeds.append((iter(parsed.entries), source_title))
        except Exception as e:
            Actor.log.warning(f"Failed to parse feed {feed_url}: {e}")

    if not parsed_feeds:
        return []

    articles = []
    feed_queue = deque(parsed_feeds)
    while len(articles) < max_articles and feed_queue:
        entry_iterator, source_title = feed_queue.popleft()
        try:
            entry = next(entry_iterator)
            article_item = Article(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                source=source_title,
                published=entry.get("published"),
                summary=entry.get("summary"),
            )
            articles.append(article_item)
            feed_queue.append((entry_iterator, source_title))
        except StopIteration:
            Actor.log.info(f"Source exhausted: {source_title}")
        except Exception as e:
            Actor.log.warning(f"Error reading entry from {source_title}: {e}. Skipping source.")

    Actor.log.info(f"Collected a total of {len(articles)} articles from RSS feeds.")
    return articles

# REMOVED: fetch_alpha_vantage_articles function


# --- DUCKDUCKGO SEARCH FUNCTION (UNCHANGED) ---
async def fetch_summary_from_duckduckgo(query: str, is_test_mode: bool, region: str, time_limit: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Performs a DuckDuckGo search. Returns a tuple: (concatenated_summary_string, list_of_structured_snippets).
    """
    if is_test_mode:
        # Returns test data matching the required structure for the DatasetRecord
        test_snippets = [{
            "title": "Local Election Results Declared", 
            "url": "https://test.bbc.com/article", 
            "source": "BBC.com", 
            "date": "2025-10-19T00:00:00Z"
        }]
        summary_text = "DuckDuckGo Test Snippet: Local elections concluded with a surprise victory for the opposing party, indicating a shift in public sentiment."
        return summary_text, test_snippets
        
    try:
        ddg_search = DuckDuckGoSearchResults(region=region, max_results=5)
        
        time_query_map = {"d": "day", "w": "week", "m": "month", "any": None}
        time_filter = time_query_map.get(time_limit, None)
        final_query = f"{query} t:{time_filter}" if time_filter else query
        
        Actor.log.info(f"Running DuckDuckGo search: {final_query}")

        search_result_str = ddg_search.run(final_query)
        
        snippets_list = []
        snippets_text = []
        
        # Regex to extract snippets, titles, and sources
        for match in re.finditer(r"\[snippet: (.*?), title: (.*?), url: (.*?)\]", search_result_str):
            snippet_text = match.group(1).replace("\\n", " ").strip()
            snippet_title = match.group(2).strip()
            snippet_url = match.group(3).strip()

            snippets_text.append(f"- {snippet_text}")
            
            # Extract source domain from URL for the 'source' field
            source_domain = urlparse(snippet_url).netloc.split('.')[-2].capitalize()

            # Structure the data for the final output (DatasetRecord)
            snippets_list.append({
                "title": snippet_title, 
                "url": snippet_url, 
                "source": source_domain, 
                "date": datetime.utcnow().isoformat() + "Z" # Mock/Current date since DDG snippet tool doesn't provide it
            })

        return "\n".join(snippets_text) if snippets_text else "", snippets_list

    except Exception as e:
        Actor.log.warning(f"DuckDuckGo search failed for query '{query}': {e}")
        return "", []


# --- LLM ANALYSIS: analyze_article_summary (Context-based Analysis) ---
async def analyze_article_summary(article: Article, is_test_mode: bool, context_for_analysis: str) -> Dict[str, Any]:
    """
    Performs LLM analysis using the provided search/summary context, then OpenAI for structured output.
    ADAPTED FOR WORLD NEWS FOCUS.
    """
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing external APIs for analysis.")
        return {"sentiment": "Moderate Urgency (TEST)", "category": "Politics/Government (TEST)", "key_entities": ["President Doe", "Paris"], "urgency_score": 5.0}

    try:
        client = init_openai()
    except ValueError:
        return {"sentiment": "Error", "category": "Error", "key_entities": [], "urgency_score": None}

    sentiment_options = ["High Urgency (Crisis/Conflict)", "Moderate Urgency (Policy/Major Event)", "Low Urgency (Routine/Lifestyle)"]
    category_list_str = ", ".join(CATEGORIES)
    
    extraction_prompt = f"""
    Analyze the following text derived from a real-time world news search or article summary: "{context_for_analysis}"

    Based ONLY on the text provided, generate a structured JSON object with the following analysis:
    1.  **sentiment**: The perceived urgency/importance (choose one: {', '.join(sentiment_options)}).
    2.  **category**: The single best thematic category from this list: {category_list_str}.
    3.  **key_entities**: A list of up to 3 key people, organizations, or locations (e.g., 'Joe Biden', 'United Nations', 'Kyiv') mentioned.
    4.  **numeric_score**: A single float between 0.0 (very low urgency/impact) and +10.0 (very high urgency/impact) reflecting the intensity of the event.

    Your entire output MUST be a single, valid JSON object. Do not include any explanation or extra text.
    """
    
    Actor.log.info("OpenAI: Extracting structured analysis from provided context.")
    try:
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        json_string = response.choices[0].message.content.strip()
        parsed = json.loads(json_string)
        sentiment = str(parsed.get("sentiment", "Low Urgency (Routine/Lifestyle)")).strip()
        
        return {
            "sentiment": sentiment if sentiment in sentiment_options else "Low Urgency (Routine/Lifestyle)",
            "category": str(parsed.get("category", "N/A")).strip(),
            "key_entities": [str(e).strip() for e in parsed.get("key_entities", [])][:3],
            "urgency_score": float(parsed.get("numeric_score", 0.0))
        }
    except APIError as e:
        Actor.log.warning(f"OpenAI structure extraction failed (API Error): {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": [], "urgency_score": None}
    except Exception as e:
        Actor.log.warning(f"OpenAI structure extraction failed: {e}")
        return {"sentiment": "Error", "category": "Error", "key_entities": [], "urgency_score": None}


# --- LLM SUMMARIZATION: generate_llm_summary ---
async def generate_llm_summary(article: Article, is_test_mode: bool) -> str:
    """Generates an AI summary for an article using the OpenAI LLM. ADAPTED PROMPT."""
    if is_test_mode:
        Actor.log.warning("ADMIN TEST MODE: Bypassing LLM summarization.")
        return f"TEST MODE SUMMARY: Summary for {article.title}."
        
    content_to_summarize = article.summary if article.summary else f"Title: {article.title}. Source: {article.source}."

    try:
        client = init_openai()
    except ValueError:
        return "LLM Summary Error: OpenAI client initialization failed."
    
    prompt = f"""
    Create a concise, one-paragraph summary of the following news article context. Focus on the main geopolitical, social, or environmental implications.
    Article Context: "{content_to_summarize}"
    Your entire output MUST be the summary text ONLY.
    """

    try:
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        Actor.log.warning(f"LLM summarization failed (API Error): {e}")
        return f"LLM Summary Error: {article.title}"
    except Exception as e:
        Actor.log.warning(f"LLM summarization failed: {e}")
        return f"LLM Summary Error: {article.title}"