from apify import Actor
from langgraph.graph import StateGraph
# FIX: Include TypedDict for WorkflowState definition
from typing import List, TypedDict, Any 
import asyncio
from .models import RSSFeed, Article, InputConfig, DatasetRecord
from .tools import (
    fetch_rss_feeds,
    generate_llm_summary,
    # New Tools
    init_openai, 
    fetch_summary_from_duckduckgo,
)
import re # Needed for strip_html_tags


# ---------------------------
# LangGraph Workflow State
# ---------------------------

class WorkflowState(TypedDict):
    """Defines the state passed between nodes in the LangGraph workflow."""
    config: InputConfig
    all_articles: List[Article] # Combined list for processing
    processed_count: int


# ---------------------------
# Utility Function (from previous steps)
# ---------------------------
def strip_html_tags(text: str) -> str:
    """A helper function to remove basic HTML tags."""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()


# ---------------------------
# Node Functions
# ---------------------------

async def process_and_save_article(state: WorkflowState) -> dict:
    """
    Processes the next article. Runs DuckDuckGo Search, then LLM analysis, then LLM summarization.
    
    The search logic uses a four-priority strategy: Strict/Time > Shortened/Time > Loose/Any Time > Shortest/Any Time.
    """
    # FIX: Ensure all state variables are extracted correctly to prevent NameError
    all_articles = state["all_articles"]
    config = state["config"]
    processed_count = state["processed_count"]
    # END FIX
    
    if processed_count >= len(all_articles):
        Actor.log.info("No more articles to process.")
        return {"processed_count": processed_count}


    art = all_articles[processed_count]
    
    # Initialize all fields with defaults
    article_sentiment = "N/A"
    article_category = "N/A"
    article_entities = []
    article_urgency_score = None 
    structured_snippets = [] 
    
    Actor.log.info(f"Processing article {processed_count + 1} of {len(all_articles)} [Source: {art.source}]: {art.url}")
    
    # --- 1. DuckDuckGo Search (Four-Priority Logic for Grounding) ---
    ai_overview = ""
    
    # --- Priority 1: Strict Quoted Search (High Precision, Time Limited) ---
    query_strict = f"\"{art.title}\""
    Actor.log.info("Priority 1: Attempting strict DuckDuckGo search (full title, limited time).")
    ai_overview, structured_snippets = await fetch_summary_from_duckduckgo(
        query=query_strict, 
        is_test_mode=config.runTestMode,
        region=config.region, 
        time_limit=config.timeLimit
    )

    # --- Priority 2: Loose Shortened Search (Noise Reduction, Time Limited) ---
    if not ai_overview:
        # Use only the first 10 words of the title to avoid overly specific long titles
        query_short_time_limit = " ".join(art.title.split()[:10]).replace('"', '').strip()
        Actor.log.warning("Priority 1 failed. Attempting Priority 2: Shortened DuckDuckGo search (limited time).")
        
        ai_overview, structured_snippets = await fetch_summary_from_duckduckgo(
            query=query_short_time_limit, 
            is_test_mode=config.runTestMode,
            region=config.region, 
            time_limit=config.timeLimit
        )

    # --- Priority 3: Loose Full Title Search (ANY Time) ---
    if not ai_overview and config.timeLimit != "any":
        query_loose_notime = art.title.replace('"', '').strip()
        Actor.log.warning(f"Priority 2 failed. Attempting Priority 3: Loose DuckDuckGo search (Time Limit removed to 'any').")
        
        ai_overview, structured_snippets = await fetch_summary_from_duckduckgo(
            query=query_loose_notime, 
            is_test_mode=config.runTestMode,
            region=config.region, 
            time_limit="any" # Force 'any' time limit
        )

    # --- Priority 4: Loose Shortened Search (ANY Time) - Final Attempt ---
    if not ai_overview and config.timeLimit != "any":
        # Use the shortest query (first 5 words) with no time limit for maximum recall
        query_short_notime = " ".join(art.title.split()[:5]).replace('"', '').strip()
        Actor.log.warning(f"Priority 3 failed. Attempting Priority 4: Shortened DuckDuckGo search (No time limit).")
        
        ai_overview, structured_snippets = await fetch_summary_from_duckduckgo(
            query=query_short_notime, 
            is_test_mode=config.runTestMode,
            region=config.region, 
            time_limit="any" # Force 'any' time limit
        )

    # Fallback: Use the cleaned RSS Summary for analysis context
    if not ai_overview and art.summary and len(art.summary.strip()) >= 50:
        Actor.log.warning("Final search priorities failed. Falling back to original RSS summary for analysis.")
        ai_overview = strip_html_tags(art.summary) 
        structured_snippets = []
        
    if not ai_overview and not config.runTestMode:
        Actor.log.error(f"❌ No AI context could be found for grounding analysis. Skipping.")
        return {"processed_count": processed_count + 1}

    # --- 2. Get Analysis Data (LLM Analysis using the found context) ---
    # Import locally to avoid circular dependency
    from .tools import analyze_article_summary 
    analysis_results = await analyze_article_summary(
        article=art,
        is_test_mode=config.runTestMode,
        context_for_analysis=ai_overview # The result of the search/fallback
    )
    
    article_sentiment = analysis_results.get("sentiment")
    article_category = analysis_results.get("category")
    article_entities = analysis_results.get("key_entities")
    article_urgency_score = analysis_results.get("urgency_score") 


    # --- 3. Perform LLM Summarization (NOW UNCONDITIONAL) ---
    final_summary = art.summary # Start with existing summary (RSS or DuckDuckGo snippets)
    
    # Call generate_llm_summary unconditionally
    llm_summary = await generate_llm_summary(art, config.runTestMode)
    
    if llm_summary and not llm_summary.startswith("LLM Summary Error"):
        final_summary = llm_summary
    else:
        # If LLM summarization fails, keep the initial summary (RSS or DuckDuckGo context)
        Actor.log.warning(f"LLM summarization failed. Keeping original context/summary.")

    # Update article object with final summary
    art.summary = final_summary
    
    # 4. Save the single article immediately to the dataset
    dataset_record = DatasetRecord(
        source=art.source,
        title=art.title,
        url=art.url,
        published=art.published,
        summary=art.summary if art.summary else "No summary available (LLM skipped or failed).",
        sentiment=article_sentiment,
        category=article_category,
        key_entities=article_entities,
        gdelt_tone=article_urgency_score, 
        snippet_sources=structured_snippets 
    # CORRECTED: This line now uses model_dump()
    ).model_dump() 

    Actor.log.info(f"Pusing record for {art.title[:50]}... to dataset. Analysis: {article_sentiment}, {article_category}")
    await Actor.push_data([dataset_record])
    
    # 5. Update the processed count for the next iteration
    return {"processed_count": processed_count + 1}


def should_continue(state: WorkflowState) -> str:
    """Conditional edge to check if more articles need processing."""
    
    all_articles = state.get("all_articles", [])
    processed_count = state["processed_count"]
    
    if processed_count < len(all_articles):
        return "continue"
    else:
        return "end"


# ---------------------------
# Main Entry Point
# ---------------------------

async def main():
    """Main entrypoint for Apify actor execution."""
    async with Actor:
        input_data = await Actor.get_input()
        
        config = InputConfig(**input_data)
        Actor.log.info(f"Loaded config: {config}")
        
        # --- NEW API KEY CHECK ---
        if not config.runTestMode:
            try:
                # The LLM is now OpenAI. Check for the new key.
                init_openai() 
            except ValueError:
                Actor.log.error("❌ Missing required API key in environment variables (OPENAI_API_KEY). Aborting execution.")
                await Actor.exit(exit_code=1)
                return
        # -------------------------

        if config.runTestMode:
            Actor.log.warning("!!! ADMIN TEST MODE ACTIVE: Actor is bypassing ALL EXTERNAL API costs. !!!")

        
        # 1. Determine Fetch Strategy and Run Fetchers
        Actor.log.info("Starting Data Fetch from RSS feeds.")
        
        # Call synchronous RSS fetcher directly.
        rss_articles = fetch_rss_feeds(
            config.source, config.customFeedUrl, config.maxArticles
        )
        
        # The articles list now only contains RSS articles
        all_articles = rss_articles
        
        Actor.log.info(f"Collected a total of {len(all_articles)} articles to process.")
        
        if not all_articles:
            Actor.log.warning("No articles collected from any source. Finishing pipeline.")
            return
            
        # 2. Setup LangGraph for Iterative Processing Loop
        graph = StateGraph(WorkflowState)
        graph.add_node("ProcessAndSaveArticle", process_and_save_article)
        graph.set_entry_point("ProcessAndSaveArticle")
        
        graph.add_conditional_edges(
            "ProcessAndSaveArticle",
            should_continue,
            {"continue": "ProcessAndSaveArticle", "end": "__end__"}
        )

        app = graph.compile()
        
        Actor.log.info("Starting iterative processing loop (OpenAI Analysis/Summarization).")
        
        # Initial state for the loop contains the combined articles
        initial_state = {
            "config": config,
            "all_articles": all_articles,
            "processed_count": 0
        }
        
        # Set recursion limit dynamically based on max articles
        max_total_articles = config.maxArticles + 5
        recursion_config = {"recursion_limit": max_total_articles}

        await app.ainvoke(initial_state, config=recursion_config)

        Actor.log.info("🎯 World News Intelligence pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())