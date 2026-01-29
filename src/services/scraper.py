import requests
from bs4 import BeautifulSoup
from apify import Actor
import re

def scrape_article_content(url: str, run_test_mode: bool) -> tuple[str | None, str | None]:
    """
    Step A: Attempt to scrape the direct URL.
    Returns (cleaned_text, image_url) or (None, None) if failed/blocked.
    """
    if run_test_mode:
        return (
            "<p>Test Content: Valve announced Half-Life 3 today. It is a VR exclusive.</p>",
            "https://placehold.co/600x400/png"
        )

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        Actor.log.info(f"🕷️ Attempting to scrape: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check for soft blocks or errors
        if response.status_code in [403, 429, 401]:
            Actor.log.warning(f"🛡️ Anti-bot trigger ({response.status_code}) on {url}. Switching to Fallback.")
            return None, None
            
        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Scrape Image (OpenGraph > Twitter > First Image)
        image_url = None
        
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content')
            
        if not image_url:
            twitter_image = soup.find('meta', name='twitter:image')
            if twitter_image:
                 image_url = twitter_image.get('content')
        
        # Heuristics for article body
        article_body = soup.find('article') or soup.find('main') or soup.find(class_=re.compile(r'content|post|article'))
        
        if article_body:
            text = article_body.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
            
        # Cleanup
        clean_text = re.sub(r'\s+', ' ', text).strip()
        
        # Quality check: if text is too short, it's likely a cookie wall or error
        if len(clean_text) < 300:
            Actor.log.warning(f"⚠️ Scraped content too short ({len(clean_text)} chars). Likely failed.")
            return None, None

        return clean_text[:8000], image_url # Truncate for LLM context limits

    except Exception as e:
        Actor.log.warning(f"Scrape error on {url}: {e}")
        return None, None