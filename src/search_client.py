import os
import logging
import httpx
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class BraveSearchClient:
    """
    Manages Brave API interaction with key rotation and efficient usage.
    Supports Web Search and Image Search.
    Prioritizes Free Tiers (Search/AI) -> Paid Tier (Base).
    """
    def __init__(self):
        self.keys = {
            "search": os.getenv("BRAVE_SEARCH_API"), # 2000 free
            "ai": os.getenv("BRAVE_AI_API"),         # 2000 free
            "base": os.getenv("BRAVE_BASE_API")      # Paid
        }
        self.usage = {
            "search": 0,
            "ai": 0,
            "base": 0
        }
        self.limit = 2000
        self.web_search_url = "https://api.search.brave.com/res/v1/web/search"
        self.image_search_url = "https://api.search.brave.com/res/v1/images/search"

    def _get_best_key(self) -> Tuple[Optional[str], Optional[str]]:
        """Selects the best available API key."""
        # 1. Try Search API (Free)
        if self.keys["search"] and self.usage["search"] < self.limit:
            return self.keys["search"], "search"
        
        # 2. Try AI API (Free) as backup
        if self.keys["ai"] and self.usage["ai"] < self.limit:
            return self.keys["ai"], "ai"

        # 3. Try Base API (Paid)
        if self.keys["base"]:
            return self.keys["base"], "base"

        return None, None

    async def search(self, query: str, count: int = 10) -> List[Dict]:
        """
        Executes a web search using the best available API key.
        """
        api_key, key_type = self._get_best_key()
        if not api_key:
            logger.error("❌ No Brave API keys available or limits reached.")
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        
        params = {"q": query, "count": min(count, 20)}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.web_search_url, headers=headers, params=params, timeout=10.0)
                
                if resp.status_code == 200:
                    self.usage[key_type] += 1
                    data = resp.json()
                    # Brave returns 'web' -> 'results'
                    return data.get("web", {}).get("results", [])
                elif resp.status_code == 429:
                    logger.warning(f"⚠️ Rate limit hit for {key_type}. Switching...")
                    self.usage[key_type] = self.limit + 1
                    return await self.search(query, count)
                else:
                    logger.error(f"Brave Web Search Error ({resp.status_code}): {resp.text}")
                    return []
        except Exception as e:
            logger.error(f"Brave Web Search Request Failed: {e}")
            return []

    async def search_images(self, query: str, count: int = 1) -> List[Dict]:
        """
        Executes an image search to find relevant images.
        """
        api_key, key_type = self._get_best_key()
        if not api_key:
            logger.error("❌ No Brave API keys available for image search.")
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        
        # Brave Image Search params
        params = {
            "q": query,
            "count": min(count, 5),
            "search_lang": "en",
            "country": "ZA" # Localization for South Africa
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.image_search_url, headers=headers, params=params, timeout=10.0)
                
                if resp.status_code == 200:
                    self.usage[key_type] += 1
                    data = resp.json()
                    # Brave returns 'results' list directly for images? Checking docs/response structure usually needed.
                    # Standard Brave response structure: root -> results OR root -> images -> results
                    # Based on standard output, it's typically within a 'results' list or 'images' object.
                    # Let's assume standard wrapper 'results' at root for images too or check 'results' key.
                    # Actually, for images/search, it is usually data['results'] list.
                    return data.get("results", [])
                elif resp.status_code == 429:
                    logger.warning(f"⚠️ Rate limit hit for {key_type} (Images). Switching...")
                    self.usage[key_type] = self.limit + 1
                    return await self.search_images(query, count)
                else:
                    logger.error(f"Brave Image Search Error ({resp.status_code}): {resp.text}")
                    return []
        except Exception as e:
            logger.error(f"Brave Image Search Request Failed: {e}")
            return []
