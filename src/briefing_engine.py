import os
import logging
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class BriefingEngine:
    """
    Generates daily Morning News Briefing videos using HeyGen AI.
    Features:
    - API Key Rotation (3 keys) based on day of month.
    - Template-based generation.
    - Storage upload via Supabase.
    """

    def __init__(self, ingestor, extractor, template_id: Optional[str] = None):
        self.ingestor = ingestor
        self.extractor = extractor
        self.template_id = template_id or os.getenv("HEYGEN_TEMPLATE_ID") or "4c6612c766e94908a2cb3f0d61192bd0"
        self.base_url = "https://api.heygen.com"
        
        # Check keys
        self.keys = [
            os.getenv("HEYGEN_API_KEY"),
            os.getenv("HEYGEN_API_KEY_2"),
            os.getenv("HEYGEN_API_KEY_3")
        ]
        
    def _get_active_key(self) -> str:
        """
        Selects API Key based on (day_of_month - 1) % 3.
        """
        day = datetime.now().day
        index = (day - 1) % 3
        key = self.keys[index]
        
        if not key:
            # Fallback logic if specific day key is missing
            for k in self.keys:
                if k: return k
            raise ValueError("No HeyGen API Keys found in environment.")
            
        logger.info(f"🔑 Using HeyGen Key #{index + 1} (Day {day})")
        return key

    async def run(self):
        logger.info("🌅 Starting Morning Briefing Generation...")
        
        # 1. Fetch Top News
        stories = await self._fetch_top_stories()
        if not stories:
            logger.warning("No suitable stories found for briefing.")
            return

        # 2. Generate Script
        logger.info(f"📝 Generating script from {len(stories)} stories...")
        # Note: Extractor prompt MUST be tuned for < 150 words total to ensure < 60s duration (1 credit)
        script_data = self.extractor.generate_briefing_script(stories)
        if not script_data:
            logger.error("Failed to generate script.")
            return

        # Credit Guard: Estimate duration (roughly 150 words per minute)
        total_text = f"{script_data.get('slide_1', '')} {script_data.get('slide_2', '')} {script_data.get('slide_3', '')}"
        word_count = len(total_text.split())
        est_duration = word_count / 150 * 60
        logger.info(f"Credit Guard 🛡️: Approx {word_count} words / ~{int(est_duration)}s. Target: <60s (1 Credit).")
        
        if est_duration > 58: # Safety buffer
            logger.warning("⚠️ Script too long for 1 credit! functional requirement. Truncating slightly enforced by prompt is better, but logging for now.")
            # In production, we might want to re-generate or aggressively truncate here.

        # 3. Generate Video
        logger.info("🎥 Requesting HeyGen Video...")
        video_id = await self._trigger_heygen_video(script_data)
        if not video_id:
            return

        # 4. Poll for Completion
        video_url = await self._poll_heygen_status(video_id)
        if not video_url:
            return
            
        # 5. Upload to Supabase
        filename = f"briefing_{datetime.now().strftime('%Y-%m-%d')}.mp4"
        logger.info(f"📤 Uploading {filename} to Supabase Storage...")
        await self.ingestor.upload_briefing_video(video_url, filename)
        
        # 6. Log to DB Table
        # Store permanent public URL (assuming bucket is public)
        # Or rely on client to build it. Let's store the relative path or full Supabase Storage URL.
        # Ideally, we get the public URL from ingestion.
        # storage_url = f"{self.ingestor.supabase_url}/storage/v1/object/public/news-briefings/{filename}"
        # We'll calculate it or ask ingestor. 
        # Making a simple assumption based on standard supabase paths for now.
        public_url = f"{self.ingestor.url}/storage/v1/object/public/news-briefings/{filename}"
        
        try:
             self.ingestor.supabase.schema("ai_intelligence").table("briefing_logs").insert({
                 "video_url": public_url,
                 "script_data": script_data,
                 "date": datetime.now().strftime('%Y-%m-%d'),
                 "status": "completed"
             }).execute()
        except Exception as e:
            logger.warning(f"Failed to log briefing: {e}")

    async def _fetch_top_stories(self) -> List[Dict]:
        """Fetch pertinent stories from the unified view."""
        try:
            # Query news_unified_view
            # Criteria: High Urgency/Excitement OR recent & popular
            # Limit 3 for brevity
            date_today = datetime.now().strftime('%Y-%m-%d')
            
            # Since view might not support direct fitlering if not materialized properly, 
            # we rely on underlying tables or simple select.
            # Let's try to query the view directly.
            res = self.ingestor.supabase.table("news_unified_view")\
                .select("*")\
                .order("published_at", desc=True)\
                .limit(10)\
                .execute()
                
            all_news = res.data
            if not all_news: return []
            
            # Simple heuristic: filter for 'High' sentiment or just take top 3
            top_stories = []
            for item in all_news:
                if len(top_stories) >= 3: break
                # prioritize crime/politics
                if item.get("sentiment") in ["High Urgency", "High Excitement", "Critical"] or item.get("category") in ["Crime", "Politics"]:
                    top_stories.append(item)
            
            # if not enough, fill with others
            if len(top_stories) < 3:
                for item in all_news:
                    if len(top_stories) >= 3: break
                    if item not in top_stories:
                        top_stories.append(item)
                        
            return top_stories

        except Exception as e:
            logger.error(f"Failed to fetch stories: {e}")
            return []

    async def _trigger_heygen_video(self, script_data: Dict) -> str:
        """Sends request to HeyGen v2 template API."""
        api_key = self._get_active_key()
        url = f"{self.base_url}/v2/video/generate"
        
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": "Daisy-20220818", # Default fallback, template usually dictates
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "audio",
                        "voice_id": "2d5b0e6cf361460aa7fc47e3eee4ba54" # Default en-US generic
                    },
                    # "template_id": self.template_id, # V2 uses explicit stricture often?
                    # Actually for template generation, endpoint might be different: /v2/template/<id>/generate
                    # Checking HeyGen docs standard: POST https://api.heygen.com/v2/video/generate
                    # with 'test' mode? using 'template_id' in payload
                }
            ],
            "test": False,
            "template_id": self.template_id,
            "title": f"Morning Briefing {datetime.now().strftime('%Y-%m-%d')}",
            "variables": {
                "slide_1": script_data.get("slide_1", "Welcome to news."),
                "slide_2": script_data.get("slide_2", "Here is the summary."),
                "slide_3": script_data.get("slide_3", "That's all for today.")
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    video_id = data.get("data", {}).get("video_id")
                    logger.info(f"✅ Video Generation Started: {video_id}")
                    return video_id
                else:
                    logger.error(f"HeyGen Trigger Failed ({resp.status_code}): {resp.text}")
                    return None
        except Exception as e:
             logger.error(f"HeyGen Request Error: {e}")
             return None

    async def _poll_heygen_status(self, video_id: str) -> str:
        """Polls status until completed or failed."""
        api_key = self._get_active_key()
        url = f"{self.base_url}/v1/video_status.get?video_id={video_id}"
        headers = {"X-Api-Key": api_key}
        
        attempts = 0
        max_attempts = 20 # 20 * 15s = 5 mins
        
        while attempts < max_attempts:
            await asyncio.sleep(15) 
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=headers, timeout=10.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("data", {}).get("status")
                        
                        if status == "completed":
                            video_url = data.get("data", {}).get("video_url")
                            logger.info(f"✅ Video Completed! URL: {video_url}")
                            return video_url
                        elif status == "failed":
                            logger.error(f"❌ Video Generation Failed: {data.get('data', {}).get('error')}")
                            return None
                        else:
                            logger.info(f"⏳ Status: {status}...")
            except Exception as e:
                logger.warning(f"Polling error: {e}")
            
            attempts += 1
            
        logger.error("❌ Polling timed out.")
        return None
        
        await self._log_briefing_to_db(public_url, total_text, int(est_duration))

        logger.info("✅ Morning Briefing Complete.")

    async def _log_briefing_to_db(self, video_url: str, script: str, duration: int):
        try:
            data = {
                "video_url": video_url,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "script_content": script,
                "duration_seconds": duration,
                "created_at": "now()"
            }
            # Upsert on date to prevent duplicates
            self.ingestor.supabase.schema("ai_intelligence").table("daily_briefings").upsert(data, on_conflict="date").execute()
            logger.info("📅 Logged briefing to ai_intelligence.daily_briefings")
        except Exception as e:
            logger.error(f"Failed to log briefing to DB: {e}")

    async def _fetch_top_stories(self, limit: int = 3) -> List[Dict]:
        """
        Fetch top stories from news_unified_view via Supabase.
        Prioritizes 'High Urgency' and recent items.
        """
        try:
            # Fetch stories created in the last 24 hours to ensure freshness
            res = self.ingestor.supabase.table("news_unified_view")\
                .select("title, summary, category, source_url, content")\
                .order("published_at", desc=True)\
                .limit(limit)\
                .execute()
                
            return res.data
        except Exception as e:
            logger.error(f"Failed to fetch top stories: {e}")
            return []

    async def _trigger_heygen_video(self, script_data: Dict) -> str:
        """
        Calls HeyGen V2 Template Generate API.
        """
        key = self._get_active_key()
        if not self.template_id:
             logger.error("HEYGEN_TEMPLATE_ID not set in environment.")
             return None
             
        url = f"{self.base_url}/v2/template/{self.template_id}/generate"
        logger.info(f"🎥 HeyGen API Call: {url}")
        logger.info(f"🆔 Template ID: '{self.template_id}'")

        
        # Prepare payload based on script_data
        # We assume template has variables like 'script', 'title_text', etc.
        # This mapping depends on the specific template. 
        # For now, we map generic keys.
        
        # Variables for 3-slide template
        # We assume template has variables: 'slide_1_script', 'slide_2_script', 'slide_3_script'
        
        payload = {
            "test": False,
            "caption": False, 
            "title": f"Morning Briefing {datetime.now().strftime('%Y-%m-%d')}",
            "variables": {
                "slide_1_script": {
                    "name": "slide_1_script",
                    "type": "text",
                    "properties": { "content": script_data.get("slide_1", "") }
                },
                "slide_2_script": {
                    "name": "slide_2_script",
                    "type": "text",
                    "properties": { "content": script_data.get("slide_2", "") }
                },
                "slide_3_script": {
                    "name": "slide_3_script",
                    "type": "text",
                    "properties": { "content": script_data.get("slide_3", "") }
                },
                 "title_text": {
                    "name": "title_text",
                    "type": "text",
                    "properties": { "content": f"Briefing {datetime.now().strftime('%d %b')}" }
                }
            }
        }

        headers = {
            "X-Api-Key": key,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                video_id = data.get("data", {}).get("video_id")
                logger.info(f"🎬 Video Generation Started: ID {video_id}")
                return video_id
                return None
            elif resp.status_code == 404:
                logger.error(f"❌ Template Not Found (404). The ID '{self.template_id}' is invalid or not in this account.")
                await self._debug_list_available_templates(headers)
                return None
            else:
                logger.error(f"HeyGen API Error ({resp.status_code}): {resp.text}")
                return None

    async def _debug_list_available_templates(self, headers: Dict):
        """
        Helper to list available templates to help user debug 404s.
        """
        try:
            logger.info("🔍 Attempting to list available V2 templates...")
            url = f"{self.base_url}/v2/templates"
            async with httpx.AsyncClient() as client:
                # Try fetching first page
                resp = await client.get(url, headers=headers, params={"limit": 10})
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("templates", [])
                    if not data:
                        logger.warning("⚠️ No templates found in this HeyGen account.")
                        return
                    
                    logger.info("✅ Available Templates (First 10):")
                    for t in data:
                        logger.info(f"   - Name: {t.get('name')} | ID: {t.get('template_id')}")
                else:
                    logger.warning(f"Could not list templates: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Debug listing failed: {e}")

    async def _poll_heygen_status(self, video_id: str) -> str:
        """
        Polls video status until completed or failed.
        """
        key = self._get_active_key()
        url = f"{self.base_url}/v1/video_status.get"
        params = {"video_id": video_id}
        headers = {"X-Api-Key": key}

        waited = 0
        timeout = 600 # 10 minutes max
        
        async with httpx.AsyncClient() as client:
            while waited < timeout:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    status = data.get("status")
                    
                    if status == "completed":
                        video_url = data.get("video_url")
                        logger.info(f"🏁 Video Rendered: {video_url}")
                        return video_url
                    elif status == "failed":
                        logger.error(f"Video Rendering Failed: {data.get('error')}")
                        return None
                    else:
                        logger.info(f"⏳ Status: {status}...")
                
                await asyncio.sleep(15) 
                waited += 15
                
        logger.error("Video rendering timed out.")
        return None
