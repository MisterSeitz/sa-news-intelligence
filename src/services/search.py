import os
import time
import requests
from apify import Actor

# Priority ordered list of Environment Variables to check
# Order: Free Tiers (Search, AI) -> Paid Tier (Base) -> Legacy Fallback
BRAVE_KEYS = [
    "BRAVE_SEARCH_API", # 2000 free, 1rps
    "BRAVE_AI_API",     # 2000 free, 1rps
    "BRAVE_BASE_API",   # Paid, 20rps
    "BRAVE_API_KEY"     # Legacy
]

# State to track current active key across function calls
current_key_idx = 0

def get_active_key():
    """Returns the first available API Key from the priority list."""
    global current_key_idx
    
    # Iterate safely through keys starting from current index
    while current_key_idx < len(BRAVE_KEYS):
        key_name = BRAVE_KEYS[current_key_idx]
        key = os.getenv(key_name)
        if key:
            return key, key_name
        # If key var not set, move to next
        current_key_idx += 1
    
    return None, None

def _perform_brave_request(endpoint: str, params: dict) -> dict | None:
    """
    Internal wrapper to handle key rotation, retries, and rate limiting.
    """
    global current_key_idx
    
    url = f"https://api.search.brave.com/res/v1/{endpoint}"
    
    last_key_name = None
    key_retries = 0
    
    while True:
        api_key, key_name = get_active_key()
        
        if not api_key:
            # Logs only if we completely run out (or never had keys)
            if current_key_idx >= len(BRAVE_KEYS):
                 Actor.log.warning("❌ All Brave API keys exhausted or missing.")
            return None

        # Reset retry counter if we switched keys
        if key_name != last_key_name:
            if last_key_name is not None:
                Actor.log.info(f"🔄 Switched to Brave Key: {key_name}")
            key_retries = 0
            last_key_name = key_name

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": "Mozilla/5.0 (compatible; SA-News-Actor/1.0)"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate Limit handling
                Actor.log.warning(f"⚠️ Brave 429 (Rate Limit) on {key_name}.")
                if key_retries == 0:
                    # First hit: Sleep and Retry same key (handle 1rps burst)
                    time.sleep(1.5)
                    key_retries += 1
                    continue
                else:
                    # Second hit: Rotate to next key
                    Actor.log.warning(f"⚠️ Persistent 429 on {key_name}. Rotating...")
                    current_key_idx += 1
                    continue

            elif response.status_code in [401, 403]:
                # Auth/Quota failure -> Rotate immediately
                Actor.log.warning(f"🚫 Brave {response.status_code} on {key_name} (Quota/Auth). Rotating...")
                current_key_idx += 1
                continue
            
            else:
                # Other errors (500, etc)
                Actor.log.warning(f"Brave API Error {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            Actor.log.error(f"Brave Request Failed: {e}")
            return None

def brave_search_fallback(query_title: str, run_test_mode: bool) -> str:
    """
    Step B: Search Text Fallback.
    """
    if run_test_mode:
        return "Source A: Valve announces HL3. Source B: Release date set for 2026."

    clean_query = query_title.replace('"', '').replace("'", "")
    Actor.log.info(f"🦁 Brave Search Fallback for: {clean_query}")
    
    params = {
        "q": clean_query,
        "count": 5,
        "extra_snippets": True,
        "search_lang": "en"
    }
    
    data = _perform_brave_request("web/search", params)
    
    if not data:
        return ""
        
    results = data.get('web', {}).get('results', [])
    if not results:
        return ""

    # Aggregate snippets
    context = "Search Results:\n"
    for item in results:
        title = item.get('title', 'No Title')
        desc = item.get('description', '')
        extra = " ".join(item.get('extra_snippets', []))
        context += f"- Title: {title}\n  Snippet: {desc} {extra}\n\n"
    
    return context[:6000]

def find_relevant_image(query: str, run_test_mode: bool) -> str | None:
    """
    Step C: Find a relevant image.
    """
    if run_test_mode:
        return "https://placehold.co/600x400/png?text=Brave+Backfill"
        
    clean_query = query.replace('"', '').replace("'", "")
    
    params = {
        "q": clean_query,
        "count": 1,
        "search_lang": "en"
    }
    
    # Using 'images/search' endpoint
    data = _perform_brave_request("images/search", params)
    
    if not data:
        return None
        
    results = data.get('results', [])
    if results:
        # Try properties first, then generic url
        item = results[0]
        return item.get('properties', {}).get('url') or item.get('url')
            
    return None