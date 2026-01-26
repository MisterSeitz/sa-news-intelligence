import csv
import asyncio
import logging
from apify import Actor
import random
import math
from .scraper import NewsScraper
from .extractor import IntelligenceExtractor
from .ingestor import SupabaseIngestor
try:
    from .crime_engine import CrimeIntelligenceEngine
except ImportError:
    CrimeIntelligenceEngine = None
    logger.warning("CrimeIntelligenceEngine module not found or failed to load.")

try:
    from .briefing_engine import BriefingEngine
except ImportError:
    BriefingEngine = None
    logger.warning("BriefingEngine module not found or failed to load.")

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
        run_mode = actor_input.get("runMode", "news_scraper")
        
        selected_source = actor_input.get("source", "all")
        custom_url = actor_input.get("customFeedUrl")
        
        logger.info(f"🚀 Starting SA News Intelligence Actor")
        logger.info(f"⚙️  Config: Mode='{run_mode}', Source='{selected_source}', Test Mode={test_mode}")

        # 1. Load Sources from CSV
        sources = []
        try:
            # Load from Actor root
            import os
            base_dir = os.path.dirname(os.path.abspath(__file__)) # src/
            actor_root = os.path.dirname(base_dir) # sa-news-intelligence/
            
            csv_path = os.path.join(actor_root, CSV_PATH)
            
            logger.info(f"📂 Reading sources from {csv_path}")
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("URL"):
                        sources.append(row)
        except Exception as e:
            logger.error(f"❌ Failed to load sources CSV: {e}")
            return

        # 2. Filter Sources based on Input
        target_sources = []
        
        if selected_source.lower() == "custom":
            if custom_url:
                target_sources = [{"Source": "Custom", "URL": custom_url, "Category": "General", "Location (If Applicable)": ""}]
                logger.info(f"🔗 Using Custom URL: {custom_url}")
            else:
                logger.error("❌ Custom source selected but no URL provided.")
                return
        elif selected_source.lower() != "all":
            # Filter by matching Source column (case-insensitive)
            target_sources = [s for s in sources if s.get("Source", "").lower() == selected_source.lower()]
            if not target_sources:
                 logger.warning(f"⚠️ No sources found matching '{selected_source}'. Checking available sources...")
                 # Optional: log available source names for debugging
                 unique_sources = set(s.get("Source") for s in sources)
                 logger.info(f"ℹ️  Available Sources: {', '.join(unique_sources)}")
        else:
            # "all" selected
            target_sources = sources

        if test_mode and len(target_sources) > 5:
             logger.info("🧪 Test Mode: Limiting to first 5 sources.")
             target_sources = target_sources[:5]

        ali_url = actor_input.get("alibabaBaseUrl")
        ali_model = actor_input.get("alibabaModel")
        extractor = IntelligenceExtractor(base_url=ali_url, model=ali_model)
        
        webhook_url = actor_input.get("webhookUrl")
        enable_backfill = actor_input.get("enableImageBackfill", True)
        ingestor = SupabaseIngestor(webhook_url=webhook_url, enable_backfill=enable_backfill)     # Relies on Env Vars
        
        # 3b. Check for Crime Intelligence Mode
        if run_mode == "crime_intelligence":
            if CrimeIntelligenceEngine:
                city_scope = actor_input.get("crimeCityScope", "major_cities")
                crime_engine = CrimeIntelligenceEngine(ingestor, extractor)
                await crime_engine.run(city_scope=city_scope)
                logger.info("✅ Crime Intelligence Run Complete.")
                return
            else:
                logger.error("❌ Crime Intelligence Engine unavailable.")
                return
        
        # 3c. Check for Morning Briefing Mode
        elif run_mode == "morning_briefing":
            if BriefingEngine:
                t_id = actor_input.get("heygenTemplateId")
                briefing_engine = BriefingEngine(ingestor, extractor, template_id=t_id)
                await briefing_engine.run()
                return
            else:
                logger.error("❌ BriefingEngine unavailable.")
                return

        if run_mode == "news_scraper":
             # 3d. Apply Diversity Logic
             # Shuffle to avoid alphabetical bias
             random.shuffle(target_sources)
             logger.info("🔀 Shuffled sources for diversity.")
             
             # Calculate Smart Limits
             global_max_articles = actor_input.get("maxArticles", 50)
             user_max_per_source = actor_input.get("maxArticlesPerSource", 5)
             source_count = len(target_sources)
             
             if source_count > 0:
                 # Distribute global limit across sources (at least 1 per source if possible)
                 smart_limit = math.ceil(global_max_articles / source_count)
                 # Respect user's max_per_source if it's lower
                 final_per_source_limit = min(user_max_per_source, smart_limit)
                 # Ensure at least 1 if global max allows
                 if final_per_source_limit < 1 and global_max_articles > 0: final_per_source_limit = 1
             else:
                 final_per_source_limit = user_max_per_source

             logger.info(f"⚖️  Smart Limit: {final_per_source_limit} articles/source (Global: {global_max_articles}, Sources: {source_count})")
        else:
             # Other modes (like crime) might differ, but safe defaults
             global_max_articles = 1000
             final_per_source_limit = actor_input.get("maxArticlesPerSource", 5)

        logger.info(f"✅ Loaded {len(target_sources)} sources to process.")
        
        total_articles_processed = 0
        
        # 4. Execution Loop
        async with NewsScraper(headless=True) as scraper:
            
            for source in target_sources:
                source_url = source.get("URL")
                category = source.get("Category")
                location = source.get("Location (If Applicable)")
                
                logger.info(f"🌍 Processing Source: {source.get('Source')} - {category} ({source_url})")
                
                
                # Check Global Limit
                if total_articles_processed >= global_max_articles:
                    logger.info(f"🛑 Global Limit Reached ({total_articles_processed}/{global_max_articles}). Stopping.")
                    break

                # 4a. Crawl for Article Links
                # Pass priority keywords for SA Context
                keywords = ["africa", "brics", "south africa", "gauteng", "cape", "zuma", "ramaphosa"]
                article_links = await scraper.get_article_links(source_url, max_links=final_per_source_limit, priority_keywords=keywords)
                
                logger.info(f"🕷️  Source {source.get('Source')} yielded {len(article_links)} articles.")
                
                # 3b. Process Each Article
                for article_url in article_links:
                    logger.info(f"📄 --> Scrape & Analyze: {article_url}")
                    
                    # Fetch content
                    # Note: We use the same fetch_article method, but now on a direct article URL
                    result = await scraper.fetch_article(article_url)
                    
                    if "error" in result:
                        logger.warning(f"⚠️ Skipping {article_url} due to error: {result['error']}")
                        continue
                    
                    # Analyze
                    # Inject CSV metadata into analysis context
                    result["csv_category"] = category
                    result["csv_location"] = location
                    result["source_name"] = source.get("Source")
                    
                    # Check for empty content
                    if not result.get("content") or len(result.get("content")) < 100:
                         logger.warning(f"⚠️ Content empty or too short for analysis: {article_url}")
                         continue
                    
                    analysis = extractor.analyze(result, test_mode=test_mode)
                    
                    if not analysis:
                        logger.warning(f"⚠️ Analysis failed or returned empty.")
                        continue
                    
                    # Ingest
                    await ingestor.ingest(analysis, result)
                    
                    total_articles_processed += 1
                    if total_articles_processed >= global_max_articles:
                        break

if __name__ == "__main__":
    asyncio.run(main())