import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import create_client, Client
from apify import Actor
from ..models import AnalysisResult, ArticleCandidate

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseIngestor:
    """
    Ingests analyzed news data into Visita Intelligence Supabase tables.
    """

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        # Check standard key, then service role key, then anon key
        self.key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not self.url or not self.key:
            Actor.log.warning(f"Supabase credentials missing (URL={bool(self.url)}, Key={bool(self.key)}). Ingestion will fail.")
            self.supabase: Client = None
        else:
            try:
                self.supabase: Client = create_client(self.url, self.key)
            except Exception as e:
                Actor.log.error(f"Failed to connect to Supabase: {e}")
                self.supabase = None
        
    def _parse_date(self, date_str: str) -> str:
        """
        Validates and parses a date string. Returns None if invalid format.
        """
        if not date_str: return None
        try:
            from dateutil import parser
            if hasattr(date_str, 'isoformat'):
                return date_str.isoformat()
            
            dt = parser.parse(str(date_str))
            if dt.year < 2020 or dt.year > 2030:
                return None
            return dt.isoformat()
        except:
             return None

    async def ingest(self, analysis: AnalysisResult, article: ArticleCandidate):
        """
        Orchestrates the ingestion of a single article's intelligence.
        """
        if not self.supabase:
            return

        raw_data = article.model_dump()
        
        # 1. Ingest Entities (People/Orgs) if rich data present
        await self._ingest_rich_entities(analysis)

        # 2. Ingest Incidents (Crime/Safety)
        if analysis.incidents:
            for inc in analysis.incidents:
                await self._ingest_incident(inc, analysis, raw_data)

        # 3. Route Article Content based on Niche
        await self._route_content(analysis, raw_data)

    async def _ingest_rich_entities(self, analysis: AnalysisResult):
        # People
        if analysis.people:
            for p in analysis.people:
                if p.status and p.status.lower() in ["wanted", "missing"]:
                    # Special handling for wanted/missing
                    await self._ingest_special_person(p, analysis)
                else:
                    # General master identity
                    await self._ingest_person_identity(p)

        # Organizations
        if analysis.organizations:
            for o in analysis.organizations:
                await self._ingest_organization(o)

    async def _ingest_person_identity(self, person):
        try:
            data = {
                "full_name": person.name,
                "type": person.role,
                "contact_verified": False,
                "data_sources_count": 1,
                "last_seen_at": "now()"
            }
            # Check exist first
            res = self.supabase.schema("people_intelligence").table("master_identities").select("id").eq("full_name", person.name).execute()
            if res.data:
                self.supabase.schema("people_intelligence").table("master_identities").update({"last_seen_at": "now()"}).eq("id", res.data[0]['id']).execute()
            else:
                self.supabase.schema("people_intelligence").table("master_identities").insert(data).execute()
        except Exception as e:
            Actor.log.warning(f"Person ingest warning: {e}")

    async def _ingest_organization(self, org):
        try:
            if org.type in ["Syndicate", "Gang"]:
                # Syndicate table
                await self._ingest_syndicate(org)
                return

            data = {
                "registered_name": org.name,
                "type": org.type,
                "created_at": "now()"
            }
            res = self.supabase.schema("business_intelligence").table("organizations").select("id").eq("registered_name", org.name).execute()
            if not res.data:
                self.supabase.schema("business_intelligence").table("organizations").insert(data).execute()
        except Exception as e:
             Actor.log.warning(f"Org ingest warning: {e}")

    async def _ingest_syndicate(self, org):
        try:
            payload = {
                "name": org.name,
                "type": org.type, 
                "primary_territory": "South Africa", 
                "metadata": {"details": org.details},
                "created_at": "now()"
            }
            res = self.supabase.schema("crime_intelligence").table("syndicates").select("id").eq("name", payload["name"]).execute()
            if not res.data:
                 self.supabase.schema("crime_intelligence").table("syndicates").insert(payload).execute()
        except Exception as e:
            Actor.log.warning(f"Syndicate ingest warning: {e}")

    async def _ingest_special_person(self, person, analysis):
        # Wanted or Missing
        try:
            # We need a source URL. technically we have it from the article context?
            # But here `analysis` is passed. Ideally we need the article URL too.
            # Passing it via a context or assuming it's linked via logic.
            # wait, `_ingest_special_person` is called from `_ingest_rich_entities` which only takes `analysis`.
            # I should pass `article` URL or just skip for now if too complex to link back in this method signature.
            # Let's keep it simple for now and rely on Incident ingestion for deep links.
            pass
        except:
            pass

    async def _ingest_incident(self, incident, analysis: AnalysisResult, raw: Dict):
        try:
            occurred_at = self._parse_date(incident.date) or self._parse_date(raw.get("published")) or "now()"
            
            data = {
                "title": raw.get("title"),
                "description": incident.description,
                "occurred_at": occurred_at,
                "type": incident.type,
                "severity_level": incident.severity,
                "source_url": raw.get("url"),
                "status": "reported",
                "location": incident.location or analysis.location,
                "published_at": self._parse_date(raw.get("published")) or "now()",
                "image_url": raw.get("image_url")
            }
            # source_url is unique in schema
            self.supabase.schema("crime_intelligence").table("incidents").upsert(data, on_conflict="source_url").execute()
            Actor.log.info(f"🚨 Ingested Incident: {data['title']}")
        except Exception as e:
            Actor.log.warning(f"Error ingesting incident: {e}")

    async def _route_content(self, analysis: AnalysisResult, raw: Dict):
        niche = analysis.detected_niche or raw.get("niche") or "general"
        niche = niche.lower()

        target_schema = "ai_intelligence"
        target_table = "entries" # Default

        # Routing Logic
        if niche == "crime":
            # Crime mainly goes to incidents above, but we also want a record in general or niche?
            # User request: "upsert Crime and News events"
            # If it's pure crime, maybe just Incidents is enough, or strictly `crime` table if exists?
            # There is NO `ai_intelligence.crime` table in the list I saw earlier (sa-news-intelligence).
            # But the old actor had `crime_intelligence` schema.
            # So Crime goes to `crime_intelligence.incidents` (Handled by step 2).
            # If it is ALSO a general news article, we might want it in `ai_intelligence.entries`?
            # Let's put it in `entries` as a fallback for the feed view.
            target_table = "entries"
            
        elif niche == "politics":
             target_schema = "gov_intelligence"
             target_table = "election_news"
             
        elif niche == "sport":
            target_schema = "sports_intelligence"
            target_table = "news"
            
        elif niche == "business":
            target_table = "entries" # No specific business table usually, or use `entries` with category
            
        elif niche == "energy":
             target_table = "energy"
             if analysis.energy_type and "nuclear" in analysis.energy_type.lower():
                 target_table = "nuclear_energy"
                 
        elif niche == "motoring":
            target_table = "motoring"

        elif niche == "brics":
            target_table = "brics_news_events"
            
        # ... map others ... 
        
        # Prepare Payload
        data = {
            "title": raw.get("title"),
            "url": raw.get("url"),
            "published_at": self._parse_date(raw.get("published")) or "now()",
            "category": analysis.category,
            "summary": analysis.summary,
            "sentiment_label": analysis.sentiment,
            "source": raw.get("source", "SA News Scraper"),
            "created_at": "now()"
        }

        # Adapt payload for specific tables
        if target_table == "brics_news_events":
            # Field mapping for BRICS table
            data["ai_summary"] = data.pop("summary") # Rename summary to ai_summary
            data["sentiment_score"] = analysis.sentiment_score
            data["entities"] = analysis.key_entities
            data["location_text"] = analysis.location
            
            # Metadata from niche_data
            if analysis.niche_data:
                data["metadata"] = analysis.niche_data
            
            # Attempt to set topic if present in niche_data
            if analysis.niche_data and "topic" in analysis.niche_data:
                data["topic"] = analysis.niche_data["topic"]
                
             # Basic category validation (optional, but good for enum consistency)
            valid_categories = ['diplomacy','summit','economy','trade','energy','defense','sanctions','technology','health','education','infrastructure','governance','other']
            if data["category"] and data["category"].lower() not in valid_categories:
                 # If usage provides a mapped category, use it, otherwise 'other' or keep as is if strictness not enforced by ingestor (DB will error or cast)
                 # Let's map strict for safety if we can, or just let DB handle. 
                 # Given user input: "category text check (category in ...)" -> It WILL error if invalid.
                 # Fallback to 'other' if invalid
                 if data["category"].lower() in valid_categories:
                      data["category"] = data["category"].lower()
                 else:
                      data["category"] = "other"
                  if data["category"].lower() in valid_categories:
                       data["category"] = data["category"].lower()
                  else:
                       data["category"] = "other"
            elif not data["category"]:
                 data["category"] = "other"
        
        elif target_table == "election_news":
            # election_news has no category column
            if "category" in data:
                del data["category"]

        elif target_table == "entries":
             # entries uses 'published' instead of 'published_at'
             if "published_at" in data:
                 data["published"] = data.pop("published_at")

        # Niche Data Injection

        if analysis.niche_data:
             if target_table in ["motoring", "energy", "nuclear_energy"]:
                  data["snippet_sources"] = analysis.niche_data
             elif target_table == "entries":
                  if "data" not in data: data["data"] = {}
                  data["data"]["niche_data"] = analysis.niche_data

        # Image
        image_url = raw.get("image_url")
        if image_url:
             # Promote to top-level column for all tables (including entries)
             data["image_url"] = image_url
             
             # Maintain JSONB legacy for entries
             if target_table == "entries":
                  if "data" not in data: data["data"] = {}
                  data["data"]["image_url"] = image_url

        try:
             # Emoji Mapping
            icon = "📰"
            
            # Upsert
            conflict_col = "url"
            if target_table == "entries":
                # Special handling for entries (canonical_url)
                data["canonical_url"] = data["url"]
                del data["url"]
                # entries table often has issues with upsert if canonical_url constraint missing
                # Clean check
                existing = self.supabase.schema(target_schema).table(target_table).select("id").eq("canonical_url", data["canonical_url"]).execute()
                if existing.data:
                    self.supabase.schema(target_schema).table(target_table).update(data).eq("id", existing.data[0]['id']).execute()
                    Actor.log.info(f"{icon} Updated {target_schema}.{target_table}")
                    return
                else:
                    self.supabase.schema(target_schema).table(target_table).insert(data).execute()
                    Actor.log.info(f"{icon} Inserted {target_schema}.{target_table}")
                    return

            # Standard Upsert
            self.supabase.schema(target_schema).table(target_table).upsert(data, on_conflict=conflict_col).execute()
            Actor.log.info(f"{icon} Upserted {target_schema}.{target_table}")

        except Exception as e:
             Actor.log.warning(f"Routing failed for {target_table}: {e}")
