import os
import logging
from typing import Dict, Any, List
from supabase import create_client, Client
from postgrest.base_request_builder import APIResponse

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseIngestor:
    """
    Ingests analyzed news data into Visita Intelligence Supabase tables.
    """

    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Prefer Service Role for ingestion
        
        if not self.url or not self.key:
            logger.error("Supabase credentials missing. Ingestion will fail.")
            self.supabase: Client = None
        else:
            try:
                self.supabase: Client = create_client(self.url, self.key)
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
                self.supabase = None

    def ingest(self, analysis_result: Dict[str, Any], raw_data: Dict[str, Any]):
        """
        Orchestrates the ingestion of a single article's intelligence.
        """
        if not self.supabase:
            logger.warning("Skipping ingestion (No Supabase connection).")
            return

        # 1. Store Raw Document (for RAG/History) behavior check
        # Assuming table ai_intelligence.source_documents exists or similar
        # For now, we'll focus on the extracted entities as per prompt
        
        # 2. Ingest Entities (People/Orgs)
        self._ingest_entities(analysis_result.get("entities", []))

        # 3. Ingest Incidents (Crime/Safety)
        self._ingest_incidents(analysis_result.get("incidents"), analysis_result, raw_data)

        # 4. Ingest Locations (Geo)
        self._ingest_locations(analysis_result.get("locations", []))

    def _ingest_entities(self, entities: List[Dict]):
        if not entities: return
        
        for ent in entities:
             # Basic upsert logic into people_intelligence.entities
             # Note: Actual schema might require specific columns like 'entity_type', 'name', 'confidence'
             try:
                 data = {
                     "name": ent.get("name"),
                     "type": ent.get("type", "Unknown"),
                     "source_first_seen": "Visita News Scraper",
                     "updated_at": "now()"
                 }
                 # Using upsert on name for now - REAL IMPLEMENTATION needs robust dedup logic
                 # self.supabase.table("people_intelligence", "entities").upsert(data, on_conflict="name").execute()
                 logger.info(f"Simulated Ingestion: Entity -> {ent.get('name')}")
             except Exception as e:
                 logger.error(f"Error ingesting entity {ent}: {e}")

    def _ingest_incidents(self, incident: Dict, analysis: Dict, raw: Dict):
        if not incident: return
        
        try:
            data = {
                "title": raw.get("title"),
                "description": incident.get("description"),
                "occurred_at": incident.get("date") or raw.get("published_date"),
                "type": incident.get("type"),
                "severity": analysis.get("sentiment"), # Map sentiment to severity
                "source_url": raw.get("url"),
                "status": "reported"
            }
            # self.supabase.table("civic_intelligence", "crime_reports").insert(data).execute()
            logger.info(f"Simulated Ingestion: Incident -> {data['title']}")
        except Exception as e:
            logger.error(f"Error ingesting incident: {e}")

    def _ingest_locations(self, locations: List[str]):
        if not locations: return
        for loc in locations:
            logger.info(f"Simulated Ingestion: Location -> {loc}")
