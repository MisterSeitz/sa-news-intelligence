import asyncio
import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client
try:
    from .search_client import BraveSearchClient
except ImportError:
    from search_client import BraveSearchClient

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BackfillImages")

# Load Env
load_dotenv()

class ImageBackfiller:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Missing Supabase Credentials")
            
        self.supabase: Client = create_client(self.url, self.key)
        self.search_client = BraveSearchClient()
        
    async def process_batch(self, table: str, limit: int = 50):
        """
        Fetch records with NO image_url and try to fill them.
        """
        logger.info(f"🔎 Scanning table '{table}' for missing images (Limit: {limit})...")
        
        # 1. Fetch rows where image_url is null
        # Helper to get table ref with schema
        try:
            query = None
            schema_name = "public"
            table_name = table
            
            if "." in table:
                parts = table.split(".")
                schema_name = parts[0]
                table_name = parts[1]
            
            # Use schema() modifier if not public, or just explicit
            # Note: supabase-py usage: client.schema("s").table("t")
            
            query_builder = self.supabase.schema(schema_name).table(table_name)
            
            if table_name == "entries":
                # For entries, checks data->>image_url
                res = query_builder.select("id, title, data")\
                    .is_("data->image_url", "null")\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .execute()
            else:
                # Standard column
                res = query_builder.select("id, title, image_url")\
                    .is_("image_url", "null")\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .execute()
                    
            rows = res.data
            logger.info(f"found {len(rows)} records to process in {schema_name}.{table_name}.")
            
            for row in rows:
                await self._backfill_row(table, row) # Pass full identifier for updates
                
        except Exception as e:
            logger.error(f"Error fetching rows: {e}")

    async def _backfill_row(self, table: str, row: Dict):
        title = row.get("title")
        if not title: return
        
        logger.info(f"🖼️ Searching for: {title}")
        try:
            images = await self.search_client.search_images(title, count=1)
            if images:
                image_url = images[0].get("thumbnail", {}).get("src") or images[0].get("url")
                logger.info(f"   ✅ Found: {image_url}")
                
                # Update DB
                # Prepare Update Query
                schema_name = "public"
                table_name = table
                if "." in table:
                    schema_name, table_name = table.split(".")
                
                query_builder = self.supabase.schema(schema_name).table(table_name)

                if table_name == "entries":
                    # Update JSONB
                    current_data = row.get("data", {}) or {}
                    current_data["image_url"] = image_url
                    current_data["backfilled"] = True
                    # Check if 'data' is top level column or inside a jsonb? It's a jsonb column "data"
                    query_builder.update({"data": current_data}).eq("id", row["id"]).execute()
                else:
                    # Update Column
                    query_builder.update({"image_url": image_url}).eq("id", row["id"]).execute()
            else:
                logger.info("   ❌ No images found.")
        except Exception as e:
            logger.error(f"   ⚠️ Update failed: {e}")

async def main():
    backfiller = ImageBackfiller()
    
    # Tables to scan
    tables = ["entries", "gov_intelligence.election_news", "sports_intelligence.news"] 
    # Add others as needed: "crime_intelligence.incidents"?
    
    for t in tables:
        await backfiller.process_batch(t, limit=20)

if __name__ == "__main__":
    asyncio.run(main())
