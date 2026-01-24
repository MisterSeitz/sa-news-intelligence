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

    async def ingest(self, analysis_result: Dict[str, Any], raw_data: Dict[str, Any]):
        """
        Orchestrates the ingestion of a single article's intelligence.
        """
        if not self.supabase:
            logger.warning("Skipping ingestion (No Supabase connection).")
            return

        # 1. Ingest Entities (People/Orgs)
        await self._ingest_entities(analysis_result.get("entities", []))

        # 2. Ingest Incidents (Crime/Safety)
        if analysis_result.get("incidents"):
             await self._ingest_incident(analysis_result.get("incidents"), analysis_result, raw_data)

        # 3. Route Article Content based on Niche
        await self._route_content(analysis_result, raw_data)

    async def _ingest_entities(self, entities: List[Dict]):
        if not entities: return
        
        for ent in entities:
             name = ent.get("name")
             type_ = ent.get("type", "Unknown")
             
             if not name: continue

             # Classify broadly as Person vs Org for destination table
             if type_ in ["Politician", "Athlete", "Civilian", "Person"]:
                 await self._ingest_person(name, type_)
             elif type_ in ["Organization", "Company", "GovernmentBody"]:
                 await self._ingest_organization(name, type_)

    async def _ingest_person(self, name: str, type_: str):
        try:
            data = {
                "full_name": name,
                "type": type_,
                "contact_verified": False,
                "data_sources_count": 1,
                "last_seen_at": "now()"
            }
            # Upsert into master_identities
            # Note: We assume 'full_name' is unique constraint or we don't care about dups for now.
            # Real prod usage should likely search first. But 'upsert' works if there's a unique constraint.
            # Schema says 'full_name' is NOT unique? If so, we might get duplicates. 
            # Ideally we'd match on exact name.
            # Using on_conflict="full_name" only works if there is a constraint.
            # Let's try simple insert and ignore error or assume fuzzy match later.
            # For this MVP step, let's Insert.
            
            # Check exist first to avoid spamming dups if no unique constraint
            res = self.supabase.table("people_intelligence", "master_identities").select("id").eq("full_name", name).execute()
            if res.data:
                # Update last_seen
                self.supabase.table("people_intelligence", "master_identities").update({"last_seen_at": "now()", "type": type_}).eq("id", res.data[0]['id']).execute()
            else:
                self.supabase.table("people_intelligence", "master_identities").insert(data).execute()
                logger.info(f"Ingested Person: {name} ({type_})")

        except Exception as e:
            logger.error(f"Error ingesting person {name}: {e}")

    async def _ingest_organization(self, name: str, type_: str):
        try:
            data = {
                "registered_name": name,
                "type": type_,
                "created_at": "now()"
            }
            # Similar check for organizations
            res = self.supabase.table("business_intelligence", "organizations").select("id").eq("registered_name", name).execute()
            if not res.data:
                self.supabase.table("business_intelligence", "organizations").insert(data).execute()
                logger.info(f"Ingested Org: {name}")
        except Exception as e:
            logger.error(f"Error ingesting org {name}: {e}")

    async def _ingest_incident(self, incident: Dict, analysis: Dict, raw: Dict):
        try:
            severity_map = {"High Urgency": 3, "Moderate Urgency": 2, "Low Urgency": 1}
            severity = severity_map.get(analysis.get("sentiment"), 1)
            
            data = {
                "title": raw.get("title"),
                "description": incident.get("description"),
                "occurred_at": incident.get("date") or raw.get("published_date"),
                "type": incident.get("type", "Unknown"),
                "severity_level": severity,
                "source_url": raw.get("url"),
                "status": "reported",
                "location": str(analysis.get("locations", [])),
                "published_at": raw.get("published_date")
            }
            # source_url is unique in schema
            self.supabase.table("crime_intelligence", "incidents").upsert(data, on_conflict="source_url").execute()
            logger.info(f"Ingested Incident: {data['title']}")
        except Exception as e:
            logger.error(f"Error ingesting incident: {e}")

    async def _route_content(self, analysis: Dict, raw: Dict):
        niche = analysis.get("niche_category", "General")
        logger.info(f"Routing content to niche: {niche}")
        
        target_table = None
        target_schema = "ai_intelligence"
        
        # Routing Logic
        if niche == "Sports":
            target_schema = "sports_intelligence"
            target_table = "news"
        elif niche == "Politics" and "election" in raw.get("title", "").lower():
            target_schema = "gov_intelligence"
            target_table = "election_news"
        elif niche == "Web3":
            target_table = "web3"
        elif niche == "Real Estate":
            target_table = "real_estate"
        elif niche == "Gaming":
            target_table = "gaming"
        elif niche == "FoodTech":
            target_table = "foodtech"
        elif niche == "VC":
            target_table = "venture_capital"
        elif niche == "Cybersecurity":
            target_table = "cybersecurity"
        elif niche == "Health":
            target_table = "health_fitness"
        else:
            # Fallback for General/Markets/Other
            target_table = "entries" 

        # Prepare Common Payload (Most niche tables in ai_intelligence share structure)
        data = {
            "title": raw.get("title"),
            "url": raw.get("url"),
            "published": raw.get("published_date"),
            "category": analysis.get("category"),
            "ai_summary": analysis.get("summary"),
            "sentiment": analysis.get("sentiment"),
            # Some tables have 'source_feed', others 'source'
            "source": "SA News Scraper",
            "created_at": "now()"
        }

        # Niche Specific Adjustments
        if target_table == "entries":
            data["summary"] = analysis.get("summary") # entries uses 'summary' VS 'ai_summary'
            del data["ai_summary"]
            data["sentiment_label"] = analysis.get("sentiment")
            del data["sentiment"]
        
        try:
            self.supabase.table(target_schema, target_table).insert(data).execute()
            logger.info(f"Ingested content to {target_schema}.{target_table}")
        except Exception as e:
            logger.error(f"Error ingesting content to {target_schema}.{target_table}: {e}")
