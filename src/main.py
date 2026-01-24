import csv
import asyncio
import logging
from apify import Actor
from .scraper import NewsScraper
from .extractor import IntelligenceExtractor
from .ingestor import SupabaseIngestor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CSV_PATH = "sources.csv"
MAX_CONCURRENT_PAGES = 3

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        test_mode = actor_input.get("test_mode", False)
        
        logger.info(f"Starting SA News Intelligence Actor (Test Mode: {test_mode})")

        # 1. Load Sources from CSV
        sources = []
            # Load from Actor root
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__)) # src/
            actor_root = os.path.dirname(base_dir) # sa-news-intelligence/
            
            csv_path = os.path.join(actor_root, CSV_PATH)
            
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