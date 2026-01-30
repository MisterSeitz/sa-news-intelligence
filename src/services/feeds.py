import feedparser
from apify import Actor
from typing import List
from ..models import ArticleCandidate, InputConfig

# Map of standard feeds (Preserving your list)
# Multi-Niche Feed Map
# SA News Feeds Map
NICHE_FEED_MAP = {
    # 🌍 General / All
    "general": {
        "enca": "https://www.enca.com/rss.xml",
        "citizen": "https://www.citizen.co.za/feed",
        "dailymaverick": "https://www.dailymaverick.co.za/rss", 
    },

    # 🚨 Crime & Safety
    "crime": {
        "iol-crime": "https://iol.co.za/rss/iol/news/crime-and-courts/"
    },

    # 🇿🇦 South Africa (National News)
    "south_africa": {
        "iol-sa": "https://iol.co.za/rss/iol/news/south-africa/",
        "citizen-sa": "https://www.citizen.co.za/news/south-africa/feed/",
        "news24-top": "https://feeds.24.com/articles/news24/topstories/rss"
    },

    # 🧱 BRICS / Geopolitics
    "brics": {
        "iol-brics": "https://iol.co.za/rss/iol/news/brics/"
    },

    # ⚡ Energy & Infrastructure
    "energy": {
         "iol-energy": "https://iol.co.za/rss/iol/news/energy/"
    },

    # 🏉 Sport
    "sport": {
        "iol-sport": "https://iol.co.za/rss/iol/sport/",
        "news24-sport": "https://feeds.24.com/articles/sport/topstories/rss"
    },

    # 💻 Tech
    "tech": {
         "iol-tech": "https://iol.co.za/rss/iol/technology/"
    },

    # 🎬 Entertainment
    "entertainment": {
        "iol-entertainment": "https://iol.co.za/rss/iol/entertainment/"
    },

    # 🏖️ Lifestyle
    "lifestyle": {
        "news24-life": "https://feeds.24.com/articles/life/topstories/rss"
    },

    # 💼 Business
    "business": {
        "iol-business": "https://iol.co.za/business/",
        "citizen-business": "https://www.citizen.co.za/business/feed/",
        "news24-business": "https://feeds.24.com/articles/business/topstories/rss" 
    },

    # 🗣️ Opinion
    "opinion": {
        "iol-opinion": "https://iol.co.za/opinion/"
    },

    # 🗳️ Politics
    "politics": {
        "iol-politics": "https://iol.co.za/news/politics/",
        "news24-politics": "https://feeds.24.com/articles/news24/topstories/rss" # Using top stories as proxy if specific politics feed missing, but request listed it here
    }
}

def fetch_feed_data(config: InputConfig) -> List[ArticleCandidate]:
    """Fetches articles from RSS feeds based on niche."""
    
    # 1. TEST MODE
    if config.runTestMode:
        Actor.log.info(f"🧪 TEST MODE: Generating dummy feed data for niche '{config.niche}'.")
        return [
            ArticleCandidate(
                title=f"[{config.niche.upper()}] Major Industry Annoucement",
                url="https://example.com/breaking-news",
                source="TestFeed",
                published="Fri, 01 Dec 2025 12:00:00 GMT",
                original_summary="A major event has occurred in the industry.",
                image_url="https://placehold.co/600x400/png"
            ),
             ArticleCandidate(
                title=f"[{config.niche.upper()}] New Innovation Revealed",
                url="https://example.com/innovation",
                source="TestFeed",
                published="Fri, 01 Dec 2025 14:00:00 GMT",
                image_url="https://placehold.co/600x400/png"
            )
        ]

    # 2. REAL MODE
    urls = []
    
    # Logic to determine which niches to fetch
    target_niches = []
    if config.niche == "all":
        target_niches = [k for k in NICHE_FEED_MAP.keys() if k != "all"]
    else:
        target_niches = [config.niche]
    
    Actor.log.info(f"Fetching feeds for niches: {target_niches}")

    for niche in target_niches:
        feed_map = NICHE_FEED_MAP.get(niche, {})
        
        if config.source == "custom" and config.customFeedUrl:
             if not urls: # Only add once
                 urls.append({"url": config.customFeedUrl, "niche": config.niche if config.niche != "all" else "general"})
             break
        
        elif config.source == "all":
            for url in feed_map.values():
                urls.append({"url": url, "niche": niche})
        
        elif config.source in feed_map:
            urls.append({"url": feed_map[config.source], "niche": niche})

    Actor.log.info(f"Found {len(urls)} feeds to process. Starting parallel fetch...")

    feed_data = []
    
    # helper for parallel execution
    def process_feed_url(entry):
        url = entry["url"]
        niche_context = entry["niche"]
        local_results = []
        try:
            # Actor.log.info(f"Fetching RSS: {url} [{niche_context}]") # Reduced noise
            feed = feedparser.parse(url)
            
            for entry_data in feed.entries:
                # Basic validation
                if not hasattr(entry_data, 'title') or not hasattr(entry_data, 'link'):
                    continue

                # TIME FILTERING
                if not is_recent(entry_data.get('published'), config.timeLimit):
                    continue
                    
                # IMAGE EXTRACTION
                image_url = None
                
                # Check 1: Media Content (often in standard RSS)
                if 'media_content' in entry_data:
                    media = entry_data.media_content
                    if isinstance(media, list) and len(media) > 0:
                         image_url = media[0].get('url')

                # Check 2: Media Thumbnail (YouTube/News style)
                if not image_url and 'media_thumbnail' in entry_data:
                    thumbnails = entry_data.media_thumbnail
                    if isinstance(thumbnails, list) and len(thumbnails) > 0:
                        image_url = thumbnails[0].get('url')

                # Check 3: Enclosures (Podcasts/legacy)
                if not image_url and 'enclosures' in entry_data:
                     for enc in entry_data.enclosures:
                         if enc.get('type', '').startswith('image/'):
                             image_url = enc.get('href')
                             break

                # Check 4: Links (Atom style)
                if not image_url and 'links' in entry_data:
                     for link in entry_data.links:
                         if link.get('type', '').startswith('image/'):
                             image_url = link.get('href')
                             break

                local_results.append(
                    ArticleCandidate(
                        title=entry_data.title,
                        url=entry_data.link,
                        source=feed.feed.get('title', 'Unknown Feed'),
                        published=entry_data.get('published'),
                        original_summary=entry_data.get('summary') or entry_data.get('description'),
                        niche=niche_context,
                        image_url=image_url
                    )
                )
        except Exception as e:
            Actor.log.error(f"Failed to fetch {url}: {e}")
        return local_results

    # Parallel Execution
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_feed_url, u) for u in urls]
        for future in concurrent.futures.as_completed(futures):
            feed_data.extend(future.result())

    # Deduplicate by URL
    seen = set()
    unique_articles = []
    for art in feed_data:
        if art.url not in seen:
            unique_articles.append(art)
            seen.add(art.url)
    
    import random
    random.shuffle(unique_articles)
    Actor.log.info(f"✅ Fetched {len(unique_articles)} recent unique articles (after time filter).")
    return unique_articles[:config.maxArticles]

# --- Helper ---
from dateutil import parser
from datetime import datetime, timedelta, timezone

def is_recent(date_str: str, time_limit: str) -> bool:
    """
    Checks if article date is within the time limit.
    """
    if not date_str: return True # If no date, assume recent/relevant
    
    try:
        pub_date = parser.parse(date_str)
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        limit_hours = 24 * 7 # Default 1 week
        if time_limit == "24h": limit_hours = 24
        elif time_limit == "48h": limit_hours = 48
        elif time_limit == "1w": limit_hours = 24 * 7
        elif time_limit == "1m": limit_hours = 24 * 30
        
        cutoff = now - timedelta(hours=limit_hours)
        
        return pub_date >= cutoff
    except:
        return True # If parse fails, include it just in case