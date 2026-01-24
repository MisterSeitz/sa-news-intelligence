import csv
import asyncio
import logging
from apify import Actor
from scraper import NewsScraper
from extractor import IntelligenceExtractor
from ingestor import SupabaseIngestor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CSV_PATH = "../../news-sites/SA_NEWS_Intelligence.csv"
MAX_CONCURRENT_PAGES = 3

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        test_mode = actor_input.get("test_mode", False)
        
        logger.info(f"Starting SA News Intelligence Actor (Test Mode: {test_mode})")

        # 1. Load Sources from CSV
        sources = []
        try:
            # Adjust path relative to where main.py is run (usually from src parent)
            # If running from actor root: src/main.py -> ../news-sites/...
            # Actually, robust way is relative to this file
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # We need to go up from src/ -> root/ -> ../reference_docs/news-sites/
            # The structure is specific to the user's workspace, but in the actor context,
            # we might need to copy the CSV or reference it directly.
            # User said: "I have saved archive pages ... in /reference_docs/news-sites/"
            # The actor is in /reference_docs/sa-news-intelligence
            
            # Let's try absolute path based on user's known workspace for local dev
            # In production Apify, we'd bundle the CSV or fetch it.
            # For now, local path:
            csv_path = os.path.join(base_dir, "..", "..", "news-sites", "SA_NEWS_Intelligence.csv")
            
            if not os.path.exists(csv_path):
                 # Fallback for when running inside the actor directory specifically
                 csv_path = os.path.join(base_dir, "..", "..", "..", "reference_docs", "news-sites", "SA_NEWS_Intelligence.csv")
            
            logger.info(f"Reading sources from {csv_path}")
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("URL"):
                        sources.append(row)
        except Exception as e:
            logger.error(f"Failed to load sources CSV: {e}")
            return

        logger.info(f"Loaded {len(sources)} sources.")
        
        # 2. Initialize Components
        extractor = IntelligenceExtractor() # Relies on Env Vars
        ingestor = SupabaseIngestor()     # Relies on Env Vars
        
        # 3. Execution Loop
        async with NewsScraper(headless=True) as scraper:
            # Limiting to first 5 sources for testing if in test mode
            target_sources = sources[:5] if test_mode else sources
            
            for source in target_sources:
                url = source.get("URL")
                category = source.get("Category")
                location = source.get("Location (If Applicable)")
                
                logger.info(f"Processing Source: {source.get('Source')} - {category} ({url})")
                
                # Fetch
                result = await scraper.fetch_article(url)
                
                if "error" in result:
                    logger.warning(f"Skipping {url} due to error: {result['error']}")
                    continue
                
                # Analyze
                # Inject CSV metadata into analysis context
                result["csv_category"] = category
                result["csv_location"] = location
                
                analysis = extractor.analyze(result, test_mode=test_mode)
                
                if not analysis:
                    logger.warning("Analysis failed or returned empty.")
                    continue
                
                # Ingest
                ingestor.ingest(analysis, result)

if __name__ == "__main__":
    asyncio.run(main())