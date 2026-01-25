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

    def __init__(self, ingestor, extractor):
        self.ingestor = ingestor
        self.extractor = extractor
        self.template_id = os.getenv("HEYGEN_TEMPLATE_ID") # User must set this
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
        script_data = self.extractor.generate_briefing_script(stories)
        if not script_data:
            logger.error("Failed to generate script.")
            return

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
        
        logger.info("✅ Morning Briefing Complete.")

    async def _fetch_top_stories(self, limit: int = 3) -> List[Dict]:
        """
        Fetch top stories from news_unified_view via Supabase.
        Prioritizes 'High Urgency' and recent items.
        """
        try:
            # We want High Urgency first, then recent
            # Assuming 'sentiment_score' or 'risk_level' maps to urgency
            # news_unified_view columns: id, title, summary, category, sentiment
            
            # Simple query: last 24h, sorted by creation? 
            # Or just take latest 5 regardless of time if volume is low?
            # Let's try published_at desc.
            
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
            else:
                logger.error(f"HeyGen API Error ({resp.status_code}): {resp.text}")
                return None

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
