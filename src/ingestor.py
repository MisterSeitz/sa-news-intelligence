import os
import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime
from supabase import create_client, Client
from postgrest.base_request_builder import APIResponse

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseIngestor:
    """
    Ingests analyzed news data into Visita Intelligence Supabase tables.
    """


    def __init__(self, url: str = None, key: str = None, webhook_url: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Prefer Service Role for ingestion
        self.webhook_url = webhook_url
        
        if not self.url or not self.key:
            logger.error("Supabase credentials missing. Ingestion will fail.")
            self.supabase: Client = None
        else:
            try:
                self.supabase: Client = create_client(self.url, self.key)
                if self.webhook_url:
                     logger.info(f"🔔 Real-Time Webhook enabled: {self.webhook_url}")
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
                "location": str(analysis.get("locations", [])),
                "published_at": self._parse_date(raw.get("published_date")) or "now()",
                "image_url": raw.get("image_url")
            }
            # source_url is unique in schema
            self.supabase.schema("crime_intelligence").table("incidents").upsert(data, on_conflict="source_url").execute()
            logger.info(f"Ingested Incident: {data['title']}")
        except Exception as e:
            logger.error(f"Error ingesting incident: {e}")

    async def _ingest_wanted(self, data: Dict):
        try:
            # Map fields to database columns
            payload = {
                "name": data.get("name"),
                "crime_type": data.get("crime_type"),
                "crime_circumstances": data.get("details") or data.get("crime_circumstances"),
                "station": data.get("station"),
                "region": data.get("region") or data.get("city"), # Brave might give city
                "gender": data.get("gender"),
                "source_url": data.get("url"),
                "created_at": "now()"
            }
            # Upsert on source_url
            self.supabase.schema("crime_intelligence").table("wanted_people").upsert(payload, on_conflict="source_url").execute()
            logger.info(f"Ingested Wanted Person: {payload['name']}")
        except Exception as e:
            logger.error(f"Error ingesting wanted person: {e}")

    async def _ingest_missing(self, data: Dict):
        try:
            payload = {
                "name": data.get("name"),
                "date_missing": self._parse_date(data.get("date_missing")),
                "details": data.get("details"),
                "region": data.get("region"),
                "station": data.get("station"),
                "source_url": data.get("url"),
                "created_at": "now()"
            }
            self.supabase.schema("crime_intelligence").table("missing_people").upsert(payload, on_conflict="source_url").execute()
            logger.info(f"Ingested Missing Person: {payload['name']}")
        except Exception as e:
            logger.error(f"Error ingesting missing person: {e}")

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
            "published": self._parse_date(raw.get("published_date")),
            "category": analysis.get("category"),
            "ai_summary": analysis.get("summary"),
            # 'sentiment' is NOT common across all tables. Removed from default.
            # Some tables have 'source_feed', others 'source'
            "source": "SA News Scraper",
            "created_at": "now()"
        }

        # Niche Data Injection
        niche_data = analysis.get("niche_data")
        if niche_data:
             # For niche tables (real_estate, etc.), they use 'snippet_sources' as a JSON dump
             if target_table in ["real_estate", "gaming", "web3", "cybersecurity", "health_fitness", "foodtech", "venture_capital"]:
                 data["snippet_sources"] = niche_data


        # Add Image URL if available (handled differently per table, but good to have in base if possible)
        # Note: 'entries' schema has data jsonb, others might have image_url column.
        image_url = raw.get("image_url")
        if image_url:
             # If table has image_url column (check schema.md)
             # election_news: yes
             # news (sports): no, uses structured_data? or just add to json? 
             # entries: no, add to data jsonb
             pass

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
                 "original_source": "SA News Scraper",
                 "image_url": image_url
             }
             if "sentiment" in data: del data["sentiment"]
             if "source" in data: del data["source"]
             if "created_at" in data: del data["created_at"]

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

            # Entries: Add image_url to data jsonb
            if image_url:
                 if "data" not in data: data["data"] = {}
                 data["data"]["image_url"] = image_url
            
            # Entries: Add niche_data to data jsonb
            if niche_data:
                 if "data" not in data: data["data"] = {}
                 data["data"]["niche_data"] = niche_data


        # Niche tables often use 'raw_context_source' or 'markdown_content'
        if target_table in ["real_estate", "gaming", "web3", "cybersecurity", "health_fitness"]:
             if raw.get("content"):
                 data["raw_context_source"] = raw.get("content")
        
        if target_table in ["foodtech", "venture_capital"]:
             if raw.get("content"):
                 data["markdown_content"] = raw.get("content")
                 data["raw_context_source"] = raw.get("content")

        # SCHEMA FIX: Map 'source' vs 'source_feed'
        # Some niche tables do NOT have a 'source' column, only 'source_feed'.
        # Tables with ONLY source_feed: real_estate, gaming, web3, cybersecurity
        if target_table in ["real_estate", "gaming", "web3", "cybersecurity"]:
            data["source_feed"] = "SA News Scraper"
            if "source" in data: del data["source"]
            
        # Tables with BOTH: foodtech, venture_capital, health_fitness, entries (source only)
        # So for the dual ones, we can just add source_feed as alias
        elif target_table in ["foodtech", "venture_capital", "health_fitness"]:
            data["source_feed"] = "SA News Scraper"
            
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
                # Emoji Mapping for Niche
                emoji_map = {
                    "sports_intelligence": "🏉",
                    "gov_intelligence": "🗳️",
                    "web3": "🪙",
                    "real_estate": "🏠",
                    "gaming": "🎮",
                    "foodtech": "🍔",
                    "venture_capital": "💰",
                    "cybersecurity": "🛡️",
                    "health_fitness": "🏥",
                    "entries": "📰",
                    "news": "📰"
                }
                icon = emoji_map.get(target_table) or emoji_map.get(target_schema, "💾")

                # For Real Estate/Gaming etc, we rely on 'url' unique constraint, but DO NOT send dedup_hash
                conflict_col = "url" 
                self.supabase.schema(target_schema).table(target_table).upsert(data, on_conflict=conflict_col).execute()
                logger.info(f"{icon} Ingested/Updated content in {target_schema}.{target_table} (URL: {raw.get('url')})")

        except Exception as e:
            logger.error(f"Failed to route content to {target_schema}.{target_table}: {e}")

    async def _ingest_syndicate(self, data: Dict):
        try:
            payload = {
                "name": data.get("name"),
                "type": data.get("type"), 
                "primary_territory": data.get("primary_territory", "Unknown"), 
                "metadata": {"details": data.get("details"), "modus_operandi": data.get("details")},
                "created_at": "now()"
            }
            # Remove 'active' as it doesn't exist
            
            res = self.supabase.schema("crime_intelligence").table("syndicates").select("id").eq("name", payload["name"]).execute()
            if res.data:
                 logger.info(f"Syndicate {payload['name']} already exists.")
            else:
                 self.supabase.schema("crime_intelligence").table("syndicates").insert(payload).execute()
                 logger.info(f"🐍 Ingested Syndicate: {payload['name']}")
        except Exception as e:
            logger.error(f"Error ingesting syndicates: {e}")

    async def ingest_full_intelligence(self, analysis: Dict, raw_meta: Dict):
        """
        Ingests the output of Deep Intelligence Analysis.
        """
        if not analysis.get("relevant", True):
            logger.info("🚫 Skipping irrelevant content (Non-SA).")
            return

        source_url = raw_meta.get("url")

        # 0. Archive Raw Intelligence (Source + AI Analysis)
        try:
             self.supabase.schema("crime_intelligence").table("structured_crime_intelligence").insert({
                 "incident_type": "deep_analysis_dump",
                 "location": "South Africa", 
                 "severity": "Info",
                 "source": source_url,
                 "incident_date": "now()",
                 "data": analysis # The full JSON
             }).execute()
             logger.info(f"💾 Archived Deep Intelligence analysis for {source_url}")
        except Exception as e:
             logger.error(f"Failed to archive raw intelligence: {e}")

        # 1. Ingest Incidents
        for inc in analysis.get("incidents", []):
            try:
                # Construct unique ID or just use source_url + index? 
                # Schema uses source_url as unique. If multiple incidents in one URL, we fail on 2nd insert.
                # Logic: One URL = One Incident report usually. 
                # If distinct incidents, we might need to append a hash to source_url or just pick the main one.
                # Let's take the first one or primary one for now to satisfy Unique Constraint.
                # OR: The schema `source_url` unique constraint limits us to 1 incident per URL.
                # We will just verify if we already ingested for this URL.
                
                payload = {
                    "title": raw_meta.get("title"),
                    "description": inc.get("description"),
                    "type": inc.get("type"),
                    "severity_level": inc.get("severity", 1),
                    "source_url": source_url,
                    "location": inc.get("location"),
                    "occurred_at": self._parse_date(inc.get("date")) or "now()",
                    "status": "verified",
                    "published_at": self._parse_date(raw_meta.get("published_date")) or "now()",
                    "full_text": raw_meta.get("full_text", ""),  # Save full scraped text
                    "image_url": raw_meta.get("image_url")
                }
                self.supabase.schema("crime_intelligence").table("incidents").upsert(payload, on_conflict="source_url").execute()
                logger.info(f"🔫 Deep Ingested Incident: {payload['type']} at {payload['location']}")
                
                # TRIGGER REAL-TIME WEBHOOK FOR HIGH SEVERITY
                sev = inc.get("severity", 1)
                # Handle int or string severity (High/3)
                is_high = False
                if isinstance(sev, int) and sev >= 3: is_high = True
                if isinstance(sev, str) and sev.lower() in ["high", "critical", "urgent"]: is_high = True
                
                if is_high:
                     await self._trigger_webhook({
                         "event": "high_severity_incident",
                         "title": payload["title"],
                         "type": payload["type"],
                         "location": payload["location"],
                         "description": payload["description"],
                         "source_url": source_url,
                         "timestamp": datetime.now().isoformat()
                     })

                # Check 1st one only for now to avoid constraint error
                break 
            except Exception as e:
                logger.error(f"Error deep-ingesting incident: {e}")

        # 2. Ingest People (Wanted/Missing/Suspects)
        for p in analysis.get("people", []):
            try:
                role = p.get("role", "").lower()
                status = p.get("status", "").lower()
                
                if status == "wanted" or role == "suspect":
                     # Wanted
                     p_data = {
                         "name": p.get("name"),
                         "crime_type": p.get("crime_type", "Wanted Suspect"),
                         "source_url": source_url + f"#{p.get('name')}", 
                         # Schema: crime_circumstances
                         "crime_circumstances": p.get("details")
                     }
                     self.supabase.schema("crime_intelligence").table("wanted_people").upsert(p_data, on_conflict="source_url").execute()
                     logger.info(f"🚔 Deep Ingested Wanted: {p.get('name')}")
                
                elif status == "missing":
                     # Missing
                     m_data = {
                         "name": p.get("name"),
                         "details": p.get("details"),
                         "source_url": source_url + f"#{p.get('name')}"
                     }
                     # Schema for missing_people: id, saps_id, name, case_ref, station, date_missing, details...
                     # It DOES have 'details'. So this block might be fine, but 'wanted_people' failed.
                     # Wait, let's verify Schema for missing_people in lines 170-171 of view_file output:
                     # "id, saps_id, name, case_ref, station, date_missing (date), details, region..."
                     # So Missing People has 'details'. Wanted People has 'crime_circumstances'.
                     # The error in log was: "Could not find the 'details' column of 'wanted_people'" -> Correct, I fixed that above.
                     # Did 'missing_people' fail? Log didn't show it, but safe to keep checking.
                     self.supabase.schema("crime_intelligence").table("missing_people").upsert(m_data, on_conflict="source_url").execute()
                     logger.info(f"🆘 Deep Ingested Missing: {p.get('name')}")
            except Exception as e:
                logger.error(f"Error deep-ingesting person: {e}")

        # 3. Ingest Orgs
        for o in analysis.get("organizations", []):
            if o.get("type") in ["Syndicate", "Gang"]:
                await self._ingest_syndicate(o)

    async def _trigger_webhook(self, payload: Dict):
        """
        Sends high-priority events to the external webhook (Next.js/Slack).
        """
        if not self.webhook_url: return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json=payload, timeout=5.0)
                if resp.status_code in [200, 201]: 
                    logger.info(f"🔔 Webhook Triggered for: {payload.get('title')}")
                else:
                    logger.warning(f"Webhook failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Webhook Trigger Error: {e}")

    def _parse_date(self, date_str: str) -> str:
        """
        Validates and parses a date string. Returns None if invalid format.
        Accepts ISO 8601 or simple YYYY-MM-DD.
        """
        if not date_str: return None
        try:
            from dateutil import parser
            # Handle if it's already a datetime object (rare but possible)
            if hasattr(date_str, 'isoformat'):
                return date_str.isoformat()
            
            dt = parser.parse(str(date_str))
            
            # Additional Sanity Check: timestamps out of Postgres range or far future/past
            if dt.year < 2020 or dt.year > 2030:
                logger.warning(f"Date {dt} out of expected range (2020-2030). Using fallback.")
                return None
                
            return dt.isoformat()

        except:
             return None

    async def upload_briefing_video(self, video_url: str, filename: str):
        """
        Downloads video from URL and uploads to Supabase Storage bucket 'news-briefings'.
        """
        try:
            # 1. Download Video
            logger.info(f"Downloading video from {video_url}...")
            async with httpx.AsyncClient() as client:
                resp = await client.get(video_url, timeout=60.0)
                if resp.status_code != 200:
                     logger.error(f"Failed to download video: {resp.status_code}")
                     return

                video_bytes = resp.content
            
            # 2. Upload to Supabase Storage
            # Requires 'news-briefings' bucket to exist and be public or have policy.
            bucket = "news-briefings"
            path = f"{filename}"
            
            logger.info(f"Uploading {len(video_bytes)} bytes to {bucket}/{path}...")
            
            # Supabase Storage Upload
            res = self.supabase.storage.from_(bucket).upload(
                file=video_bytes,
                path=path,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
            
            logger.info(f"✅ Video Uploaded Successfully: {path}")

        except Exception as e:
            logger.error(f"Failed to upload briefing video: {e}")

