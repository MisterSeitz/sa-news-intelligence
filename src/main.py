import asyncio
from typing import TypedDict, List
from apify import Actor
from langgraph.graph import StateGraph, END
import os 

from .models import InputConfig, ArticleCandidate, DatasetRecord
from .services.feeds import fetch_feed_data
from .services.scraper import scrape_article_content
from .services.search import brave_search_fallback, find_relevant_image
from .services.llm import analyze_content
from .services.notifications import send_discord_alert
from supabase import create_client, Client

# --- HELPER: Ingestor ---
from .services.ingestor import SupabaseIngestor

# --- State Definition ---
class WorkflowState(TypedDict):
    config: InputConfig
    articles: List[ArticleCandidate]
    current_index: int

# --- Nodes ---

async def fetch_feeds_node(state: WorkflowState):
    """Initializes and fetches RSS data."""
    config = state['config']
    articles = fetch_feed_data(config)
    Actor.log.info(f"📚 Queued {len(articles)} articles for analysis.")
    return {"articles": articles, "current_index": 0}

async def process_article_node(state: WorkflowState):
    """The Core Logic: Scrape -> Fallback -> AI -> Save"""
    config = state['config']
    idx = state['current_index']
    articles = state['articles']
    
    if idx >= len(articles):
        return {"current_index": idx} 

    article = articles[idx]
    
    # Initialize Ingestor (Stateful per call, or singleton? Init here to ensure env vars)
    ingestor = SupabaseIngestor()

    Actor.log.info(f"👉 [{idx+1}/{len(articles)}] Processing: {article.title}")

    # 0. STRATEGY: Deduplication Check (Optional: Ingestor handles upserts, but we can skip early)
    # The new Ingestor doesn't expose a simple check public method easily without init. 
    # But since we upsert, we can just proceed.
    # Cost saving: Skip scraping if we really want to.
    # Let's rely on upsert for now to ensure data freshness or "forceRefresh".

    article_niche = getattr(article, 'niche', None) or config.niche
    if article_niche == 'all': article_niche = 'general'

    # 1. STRATEGY: Scrape First
    context, scraped_image = scrape_article_content(article.url, config.runTestMode)
    method = "scraped"
    
    final_image_url = article.image_url or scraped_image

    # 2. STRATEGY: Search Fallback
    if not context:
        Actor.log.info("⚠️ Scraping failed/blocked. Engaging Brave Search Fallback.")
        context = brave_search_fallback(article.title, config.runTestMode)
        method = "search_fallback"
        
    # 3. STRATEGY: Brave Image Backfill
    if not final_image_url and config.enableBraveImageBackfill:
         Actor.log.info(f"🖼️ Backfilling image for: {article.title}")
         final_image_url = find_relevant_image(article.title, config.runTestMode)
         # Update article model for consistency (optional, but passed to ingestor)
         article.image_url = final_image_url

    # 3. AI Analysis & Ingestion
    if context:
        try:
            # Analyze
            analysis = analyze_content(context, niche=article_niche, run_test_mode=config.runTestMode)
            
            # --- DYNAMIC ROUTING (Re-routing) ---
            if analysis.detected_niche:
                 # Clean up detected niche
                 d_niche = analysis.detected_niche.lower().strip()
                 valid_niches = ["crime", "politics", "business", "sport", "energy", "motoring"]
                 if d_niche in valid_niches:
                     Actor.log.info(f"🔀 Re-routing '{article_niche}' -> '{d_niche}'")
                     article_niche = d_niche
            
            # 4. Monetization
            if not config.runTestMode:
                await Actor.charge(event_name="summarize_snippets_with_llm")

            # 5. Ingest (Supabase)
            # We pass the analysis result (Models) and the article candidate
            # Ingestor handles: splitting incidents, people, main entry, and routing tables.
            await ingestor.ingest(analysis, article)
            
            # 6. Legacy Dataset Push (Apify Storage)
            # Create a flat record for the Apify Dataset view
            record = DatasetRecord(
                niche=article_niche,
                source_feed=article.source,
                title=article.title,
                url=article.url,
                image_url=final_image_url,
                published=article.published,
                method=method,
                sentiment=analysis.sentiment,
                category=analysis.category,
                key_entities=analysis.key_entities,
                ai_summary=analysis.summary,
                location=analysis.location,
                city=analysis.city,
                country=analysis.country,
                is_south_africa=analysis.is_south_africa,
                raw_context_source=context[:200] + "...",
                # Niche specifics (Generic mapping)
                game_studio=analysis.game_studio,
                niche_data=analysis.niche_data # Map dictionary if supported
            )
            await Actor.push_data(record.model_dump())
            Actor.log.info("✅ Data pushed to Apify dataset.")

            # 7. Notifications
            if config.discordWebhookUrl and "High Urgency" in analysis.sentiment:
                await send_discord_alert(config.discordWebhookUrl, record.model_dump())
            
        except Exception as e:
            Actor.log.error(f"Analysis loop failed for {article.title}: {e}")
    else:
        Actor.log.error("❌ Failed to gather ANY context. Skipping.")

    return {"current_index": idx + 1}

def should_continue(state: WorkflowState):
    if state['current_index'] < len(state['articles']):
        return "process_article"
    return END

# --- Main Entry ---

async def main():
    async with Actor:
        raw_input = await Actor.get_input() or {}
        config = InputConfig(**raw_input)
        
        # --- MAINTENANCE FIX ---
        if not config.runTestMode:
            if not os.getenv("OPENROUTER_API_KEY"):
                Actor.log.warning("⚠️ OPENROUTER_API_KEY not found. Switching to TEST MODE.")
                config.runTestMode = True
            elif not (os.getenv("BRAVE_API_KEY") or os.getenv("BRAVE_SEARCH_API")):
                Actor.log.warning("⚠️ BRAVE_API_KEY / BRAVE_SEARCH_API missing. Search fallback disabled.")

        # Graph Setup
        workflow = StateGraph(WorkflowState)
        workflow.add_node("fetch_feeds", fetch_feeds_node)
        workflow.add_node("process_article", process_article_node)
        
        workflow.set_entry_point("fetch_feeds")
        workflow.add_conditional_edges("fetch_feeds", lambda x: "process_article")
        workflow.add_conditional_edges("process_article", should_continue)
        
        app = workflow.compile()
        
        await app.ainvoke({
            "config": config,
            "articles": [],
            "current_index": 0
        })

if __name__ == '__main__':
    asyncio.run(main())