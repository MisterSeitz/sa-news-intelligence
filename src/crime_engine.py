import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from supabase import create_client, Client

from search_client import BraveSearchClient

logger = logging.getLogger(__name__)



class CrimeIntelligenceEngine:
    def __init__(self, ingestor, extractor):
        self.ingestor = ingestor
        self.extractor = extractor
        self.brave = BraveSearchClient()
        self.supabase: Client = ingestor.supabase # Reuse connection
        
    async def run(self, city_scope: str = "major_cities"):
        logger.info(f"🚨 Starting Crime Intelligence Run (Scope: {city_scope})")
        
        # 1. Fetch Target Cities
        cities = await self._fetch_cities(city_scope)
        logger.info(f"🎯 Targeting {len(cities)} cities/regions.")
        
        # 2. Process Each City
        for city_obj in cities:
            city = city_obj.get("name")
            logger.info(f"🏙️  Scanning algorithms for: {city}")
            
            # 2a. Search for Incidents
            await self._scan_incidents(city)
            
            # 2b. Search for Wanted/Missing
            await self._scan_people(city)
            
    async def _fetch_cities(self, scope: str) -> List[Dict]:
        """
        Queries geo_intelligence.cities or uses hardcoded major list if checking schema fails.
        """
        major_cities_list = ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Gqeberha", "Bloemfontein", "Soweto", "Sandton", "Centurion"]
        
        if scope == "major_cities":
            return [{"name": c} for c in major_cities_list]
        
        # For all_cities, fetch from Supabase
        try:
            # Fetch names from geo_intelligence.cities
            # We limit to 50 per run to avoid timeout/rate-limit in this sequential loop, 
            # ideally this should be paginated or distributed.
            res = self.supabase.schema("geo_intelligence").table("cities").select("name").limit(50).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Could not fetch cities from DB: {e}. Defaulting to majors.")
            
        return [{"name": c} for c in major_cities_list]

    async def _scrape_text(self, url: str) -> str:
        """Fetch and extract text from URL using HTTPX + BS4 (Fast)"""
        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
                resp = await client.get(url, timeout=15.0)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Remove script/style
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.extract()
                    return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
        return ""

    async def _process_deep_hit(self, url: str, title: str, date_str: str):
        """Pipeline: Scrape -> Deep Analyze -> Ingest"""
        logger.info(f"⬇️ Deep Scraping: {url}")
        text = await self._scrape_text(url)
        if len(text) < 200:
            logger.warning(f"⚠️ Content too short/empty for {url}. Skipping deep analysis.")
            return

        logger.info(f"🧠 Deep Analyzing ({len(text)} chars)...")
        deep_data = self.extractor.analyze_deep_intelligence(text, url)
        
        raw_meta = {
            "title": title,
            "url": url,
            "published_date": date_str,
            "full_text": text
        }
        
        await self.ingestor.ingest_full_intelligence(deep_data, raw_meta)

    async def _scan_incidents(self, city: str):
        # Expanded Query Strategy for Robustness
        base_keywords = [
            "crime incident",
            "murder killing homicide",
            "rape sexual assault GBV",
            "armed robbery hijacking",
            "cash in transit heist CIT",
            "gang violence shooting",
            "fraud scam alert",
            "extortion construction mafia",
            "protest unrest strike"
        ]
        
        for keyword in base_keywords:
            # Enforce "South Africa" context to avoid international ambiguity (e.g. Beacon Bay vs Beacon NY)
            q = f"{keyword} {city} South Africa news"
            
            results = await self.brave.search(q, count=5)
            logger.info(f"🔎 found {len(results)} results for query: '{q}'")
            for res in results:
                title = res.get("title")
                url = res.get("url")
                desc = res.get("description")
                date_str = res.get("age") # e.g. "2 hours ago"
                
                # Analyze Snippet (Gatekeeper)
                snippet_analysis = self.extractor.analyze_crime_snippet(desc, q)
                
                # If Snippet is a Dict (valid) and type is Relevant
                if isinstance(snippet_analysis, dict):
                    c_type = snippet_analysis.get("type")
                    if c_type in ["Incident", "Wanted", "Missing", "Syndicate"]:
                        logger.info(f"✨ Relevant Snippet ({c_type}). Promoting to Deep Analysis.")
                        await self._process_deep_hit(url, title, date_str)

    async def _scan_people(self, city: str):
        queries = [
            f"wanted suspects {city} South Africa police",
            f"missing person {city} South Africa saps",
            f"most wanted criminals {city} South Africa"
        ]
        
        for q in queries:
            results = await self.brave.search(q, count=5)
            logger.info(f"🕵️‍♂️ found {len(results)} results for query: '{q}'")
            for res in results:
                title = res.get("title")
                url = res.get("url")
                desc = res.get("description")
                date_str = res.get("age")
                
                snippet_analysis = self.extractor.analyze_crime_snippet(desc, q)
                
                if isinstance(snippet_analysis, dict):
                    c_type = snippet_analysis.get("type")
                    if c_type in ["Incident", "Wanted", "Missing", "Syndicate"]:
                         logger.info(f"✨ Relevant Person Snippet ({c_type}). Promoting to Deep Analysis.")
                         await self._process_deep_hit(url, title, date_str)
