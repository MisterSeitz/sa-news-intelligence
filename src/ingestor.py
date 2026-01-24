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
             inc_data = analysis_result.get("incidents")
             if isinstance(inc_data, list):
                 for inc in inc_data:
                     await self._ingest_incident(inc, analysis_result, raw_data)
             else:
                 await self._ingest_incident(inc_data, analysis_result, raw_data)

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
            # Check exist first to avoid spamming dups if no unique constraint
            # Use .schema() for non-public schemas
            res = self.supabase.schema("people_intelligence").table("master_identities").select("id").eq("full_name", name).execute()
            if res.data:
                # Update last_seen
                self.supabase.schema("people_intelligence").table("master_identities").update({"last_seen_at": "now()", "type": type_}).eq("id", res.data[0]['id']).execute()
            else:
                self.supabase.schema("people_intelligence").table("master_identities").insert(data).execute()
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
            res = self.supabase.schema("business_intelligence").table("organizations").select("id").eq("registered_name", name).execute()
            if not res.data:
                self.supabase.schema("business_intelligence").table("organizations").insert(data).execute()
                logger.info(f"Ingested Org: {name}")
        except Exception as e:
            logger.error(f"Error ingesting org {name}: {e}")

    async def _ingest_incident(self, incident: Dict, analysis: Dict, raw: Dict):
        try:
            severity_map = {"High Urgency": 3, "Moderate Urgency": 2, "Low Urgency": 1}
            severity = severity_map.get(analysis.get("sentiment"), 1)
            severity = severity_map.get(analysis.get("sentiment"), 1)
            
            # Safe Date Parsing
            occurred_at = self._parse_date(incident.get("date")) or raw.get("published_date") or "now()"
            
            data = {
                "title": raw.get("title"),
                "description": incident.get("description"),
                "occurred_at": occurred_at,
                "type": incident.get("type", "Unknown"),
                "severity_level": severity,
                "source_url": raw.get("url"),
                "status": "reported",
                "location": str(analysis.get("locations", [])),
                "published_at": raw.get("published_date")
            }
            # source_url is unique in schema
            # source_url is unique in schema
            self.supabase.schema("crime_intelligence").table("incidents").upsert(data, on_conflict="source_url").execute()
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
            "category": analysis.get("category"),
            "ai_summary": analysis.get("summary"),
            # 'sentiment' is NOT common across all tables. Removed from default.
            # Some tables have 'source_feed', others 'source'
            "source": "SA News Scraper",
            "created_at": "now()"
        }

        # Niche Specific Adjustments
        if target_table == "news" and target_schema == "sports_intelligence":
             # Sports specific schema mapping
             data["summary"] = analysis.get("summary")
             if "ai_summary" in data: del data["ai_summary"]
             
             if "published" in data:
                 data["published_at"] = data["published"]
                 del data["published"]
                 
             # Extract domain for source_domain
             try:
                 from urllib.parse import urlparse
                 domain = urlparse(data.get("url", "")).netloc.replace("www.", "")
                 data["source_domain"] = domain
             except:
                 data["source_domain"] = "unknown"
                 
             # Handle sentiment: Schema has sentiment_score (numeric), not text
             urgency_map = {"High Urgency": 9, "Moderate Urgency": 5, "Low Urgency": 2}
             score = urgency_map.get(analysis.get("sentiment"), 5)
             data["sentiment_score"] = score
             
             # Move extras to structured_data
             data["structured_data"] = {
                 "sentiment_label": analysis.get("sentiment"),
                 "original_source": "SA News Scraper"
             }
             if "sentiment" in data: del data["sentiment"]
             if "source" in data: del data["source"]

        elif target_table == "entries":
            data["summary"] = analysis.get("summary") # entries uses 'summary' VS 'ai_summary'
            if "ai_summary" in data: del data["ai_summary"]
            
            data["sentiment_label"] = analysis.get("sentiment")
            if "sentiment" in data: del data["sentiment"]
            
            # Map 'published' -> 'published_date' for entries table
            if "published" in data:
                data["published_date"] = data["published"]
                del data["published"]
            
            # Map content -> content (for entries)
            if raw.get("content"):
                data["content"] = raw.get("content")

        # Niche tables often use 'raw_context_source' or 'markdown_content'
        if target_table in ["real_estate", "gaming", "web3", "cybersecurity", "health_fitness"]:
             if raw.get("content"):
                 data["raw_context_source"] = raw.get("content")
        
        if target_table in ["foodtech", "venture_capital"]:
             if raw.get("content"):
                 data["markdown_content"] = raw.get("content")
                 data["raw_context_source"] = raw.get("content")
        
        # Handle Sentiment / Risk Level per table
        sentiment_text = analysis.get("sentiment", "Moderate Urgency")
        urgency_map = {"High Urgency": 3, "Moderate Urgency": 2, "Low Urgency": 1} # Simple int map
        
        if target_table == "entries":
             data["sentiment_label"] = sentiment_text
             # entries also has sentiment_score (float)
             data["sentiment_score"] = float(urgency_map.get(sentiment_text, 2))
             
             # Entries uses canonical_url instead of url
             if "url" in data:
                 data["canonical_url"] = data["url"]
                 del data["url"]
             
        elif target_table == "web3":
             # web3 uses sentiment (integer)
             data["sentiment"] = urgency_map.get(sentiment_text, 2)
             data["trading_signal"] = sentiment_text # Map text to signal just in case
             
        elif target_table == "cybersecurity":
             # cybersecurity uses risk_level (text)
             data["risk_level"] = sentiment_text
             
        elif target_table in ["gaming", "foodtech", "venture_capital", "health_fitness"]:
             # These use sentiment (text)
             data["sentiment"] = sentiment_text
             
        # real_estate HAS NO sentiment column, so we do nothing.
        
        try:
            # Deduplication: Use upsert based on unique URL
            # Also generate dedup_hash ONLY for tables that support it (entries, etc.)
            import hashlib
            
            # Check if this table supports dedup_hash (based on schema)
            # Most niche tables (real_estate, gaming, etc.) DO NOT have it.
            tables_with_hash = ["entries", "trends", "feed_items"]
            
            # Note: For entries, we deleted 'url' but we still have the original raw 'url' if needed
            # But the hash should be on the url.
            source_url = raw.get("url")
            
            if source_url and target_table in tables_with_hash:
                data["dedup_hash"] = hashlib.md5(source_url.encode()).hexdigest()

            # SPECIAL HANDLING FOR entries:
            # The 'entries' table seems to lack a unique constraint on canonical_url in the DB schema,
            # causing 42P10 error on upsert. We must do a manual check.
            if target_table == "entries":
                # Check existence via canonical_url
                c_url = data.get("canonical_url")
                if c_url:
                    existing = self.supabase.schema(target_schema).table(target_table).select("id").eq("canonical_url", c_url).execute()
                    if existing.data:
                        # Update
                        eid = existing.data[0]['id']
                        self.supabase.schema(target_schema).table(target_table).update(data).eq("id", eid).execute()
                        logger.info(f"Updated content in {target_schema}.{target_table} (ID: {eid})")
                    else:
                        # Insert
                        self.supabase.schema(target_schema).table(target_table).insert(data).execute()
                        logger.info(f"Ingested content to {target_schema}.{target_table} (New)")
                else:
                    logger.warning("Skipping entries ingestion: No canonical_url")

            else:
                # For other tables (real_estate, gaming, etc), they have 'url' unique constraint.
                # Use standard upsert.
                conflict_col = "url" 
                self.supabase.schema(target_schema).table(target_table).upsert(data, on_conflict=conflict_col).execute()
                logger.info(f"Ingested/Updated content in {target_schema}.{target_table} (URL: {raw.get('url')})")

        except Exception as e:
            logger.error(f"Error ingesting content to {target_schema}.{target_table}: {e}")
        except Exception as e:
            logger.error(f"Error ingesting content to {target_schema}.{target_table}: {e}")

    def _parse_date(self, date_str: str) -> str:
        """
        Validates and parses a date string. Returns None if invalid format.
        Accepts ISO 8601 or simple YYYY-MM-DD.
        """
        if not date_str: return None
        try:
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.isoformat()
        except:
             # Basic check for YYYY encoded in string (e.g. "2024-2025") - treat as invalid
             return None
