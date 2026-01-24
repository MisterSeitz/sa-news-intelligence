import asyncio
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import logging
from apify import Actor

# Configure logging
logger = logging.getLogger(__name__)

class NewsScraper:
    """
    Handles fetching and content extraction from news websites.
    Uses Playwright for dynamic content and falls back to simple parsing where appropriate.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def fetch_article(self, url: str) -> Dict[str, Optional[str]]:
        """
        Fetches a single article URL and extracts metadata and content.
        """
        if not self.browser:
            raise RuntimeError("NewsScraper context not started. Use 'async with NewsScraper() as scraper:'.")

        # Create a new context with a specific user agent
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page: Page = await context.new_page()
        try:
            logger.info(f"Navigating to {url}")
            
            response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            if not response or not response.ok:
                logger.error(f"Failed to load page: {url} (Status: {response.status if response else 'None'})")
                # Close the context if we fail here
                await context.close()
                return {"error": f"HTTP {response.status if response else 'Unknown'}"}

            # Wait a bit for dynamic content if needed (heuristics could be added here)
            # await page.wait_for_timeout(2000)

            content = await page.content()
            result = self._extract_content(content, url)
            
            await context.close()
            return result

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            await context.close()
            return {"error": str(e)}
        # No finally block needed for page.close() as context.close() handles it

    def _extract_content(self, html_content: str, url: str) -> Dict[str, Optional[str]]:
        """
        Parses HTML using BeautifulSoup to extract structured data.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Title Extraction
        title = None
        # Try OpenGraph first
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content")
        
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
        
        if not title:
            title = soup.title.string if soup.title else "Unknown Title"

        # 2. Date Extraction
        published_date = None
        # Try standard meta tags
        meta_date = soup.find("meta", property="article:published_time") or \
                    soup.find("meta", itemprop="datePublished") or \
                    soup.find("time")
        
        if meta_date:
            published_date = meta_date.get("content") or meta_date.get("datetime")
        
        # 3. Content Body Extraction (Heuristic)
        # Remove scripts, styles, navs
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()

        # Find the main text container - this is tricky and site specific, 
        # but p tags in 'article' or 'main' are usually good bets.
        article_body = soup.find("article")
        if not article_body:
            article_body = soup.find("main")
        
        if not article_body:
            # Fallback: Just grab all p tags if no semantic container
            article_body = soup
        
        paragraphs = article_body.find_all("p")
        text_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])

        return {
            "url": url,
            "title": title,
            "published_date": published_date,
            "content": text_content,
            "raw_html_snippet": str(article_body)[:5000] # store truncated raw html for debugging/AI
        }
