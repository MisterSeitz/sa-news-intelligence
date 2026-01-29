import os
import requests
from apify import Actor

def brave_search_fallback(query_title: str, run_test_mode: bool) -> str:
    """
    Step B: Paid Fallback using Brave Search API.
    Used when direct scraping fails.
    """
    if run_test_mode:
        return "Source A: Valve announces HL3. Source B: Release date set for 2026."

    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        Actor.log.error("❌ BRAVE_API_KEY missing in Secrets.")
        return ""

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    
    # Clean title for query
    clean_query = query_title.replace('"', '').replace("'", "")
    
    try:
        Actor.log.info(f"🦁 Brave Search Fallback for: {clean_query}")
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": clean_query,
                "count": 5,
                "extra_snippets": True, # Crucial for AI context
                "search_lang": "en"
            },
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('web', {}).get('results', [])
            
            # Aggregate snippets
            context = "Search Results:\n"
            for item in results:
                title = item.get('title', 'No Title')
                desc = item.get('description', '')
                extra = " ".join(item.get('extra_snippets', []))
                context += f"- Title: {title}\n  Snippet: {desc} {extra}\n\n"
            
            return context[:6000]
        else:
            Actor.log.warning(f"Brave API Error: {response.status_code}")
            return ""

    except Exception as e:
        Actor.log.error(f"Brave Search failed: {e}")
        return ""

def find_relevant_image(query: str, run_test_mode: bool) -> str | None:
    """
    Step C: Find a relevant image using Brave Search.
    """
    if run_test_mode:
        return "https://placehold.co/600x400/png?text=Brave+Backfill"
        
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return None
        
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    
    clean_query = query.replace('"', '').replace("'", "")
    
    try:
        # Brave Search Images Endpoint would be ideal, but for now we look at general search 'images' slot or use 'search_lang=en'
        # Actually Brave has a dedicated images endpoint: https://api.search.brave.com/res/v1/images/search
        response = requests.get(
            "https://api.search.brave.com/res/v1/images/search",
            params={
                "q": clean_query,
                "count": 1,
                "search_lang": "en"
            },
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                return results[0].get('properties', {}).get('url') # High res url usually here
            
    except Exception as e:
         Actor.log.warning(f"Brave Image Search failed for {query}: {e}")
         
    return None