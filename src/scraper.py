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

    async def get_article_links(self, start_url: str, max_links: int = 5) -> List[str]:
        """
        Crawls a section/archive page to find individual article URLs.
        """
        if not self.browser:
            raise RuntimeError("NewsScraper context not started.")

        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        links = set()
        
        try:
            logger.info(f"🕷️ Crawling listing page: {start_url}")
            response = await page.goto(start_url, timeout=30000, wait_until="domcontentloaded")
            if not response or not response.ok:
                logger.error(f"❌ Failed to load listing page: {start_url}")
                return []

            # Wait for some content
            try:
                await page.wait_for_selector("a", timeout=5000)
            except:
                pass

            # Heuristic 1: Look for links inside article tags or headings
            # Common patterns: article h3 a, h2 a, div.post a
            # We'll grab all 'a' tags and filter carefully
            
            # Evaluate js to get links to avoid transferring lots of data
            # Filter: 
            # 1. Must be http/https
            # 2. Must be same domain (approx)
            # 3. Path length > 10 (avoid home/contact)
            # 4. Not in excluding words
            
            domain = start_url.split("/")[2]
            
            found_links = await page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                return links.map(a => a.href);
            }''')
            
            for link in found_links:
                if len(links) >= max_links * 2: # Harvest more then prune
                    break
                    
                if domain not in link: continue
                if len(link) < 25: continue # Too short to be deep article
                
                # Exclude common non-article paths
                exclude = ["/category/", "/author/", "/tag/", "/section/", "/contact", "/about", "/login", "/register", "javascript:", "#", 
                           "business-maverick", "maverick-life", "maverick-citizen", "maverick-sports", "/opinion/"]
                if any(x in link.lower() for x in exclude):
                    continue
                
                # Heuristic: Valid articles usually have a date or 'article' or significant depth
                # Daily Maverick: /article/2025-01-01...
                # IOL: /news/politics/slug... (depth 3)
                
                import re
                has_date = bool(re.search(r'202[3-6]', link))
                has_article_slug = "/article/" in link
                
                # Check path depth (segments after domain)
                path = link.split(domain)[-1].strip("/")
                depth = len(path.split("/"))
                
                # If it looks like a section (low depth, no date/article keyword), skip it
                if depth < 2 and not (has_date or has_article_slug):
                     # logger.debug(f"Skipping probable section page (depth {depth}): {link}")
                     continue
                
                # Exclude non-HTML extensions (PDFs are causing "Download starting" errors)
                if any(link.lower().endswith(ext) for ext in [".pdf", ".jpg", ".png", ".jpeg", ".gif", ".zip", ".mp4", ".mp3", ".xml", ".rss"]):
                    # logger.debug(f"Skipping binary file: {link}")
                    continue

                if link == start_url or link == start_url + "/": continue
                
                links.add(link)
                
            logger.info(f"Found {len(links)} potential article links on {start_url}")

        except Exception as e:
            logger.error(f"Error crawling {start_url}: {e}")
        finally:
            await context.close()
            
        return list(links)[:max_links]

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
        for script in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript"]):
            script.decompose()

        # Specific selectors for known sites
        article_body = None
        
        # Daily Maverick & WordPress sites often use these
        selectors = [
            "div.entry-content", 
            "div.article-body", 
            "div.article__body", 
            "section.article-content",
            "article"
        ]
        
        for selector in selectors:
            found = soup.select_one(selector)
            if found:
                article_body = found
                break
        
        if not article_body:
            article_body = soup.find("main")
        
        if not article_body:
            # Fallback: Just grab all p tags if no semantic container
            article_body = soup
        
        # Extract text from paragraphs, but filter out very short ones (links, disclaimers)
        paragraphs = article_body.find_all("p")
        valid_paragraphs = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
        
        # If paragraph extraction yields little, try getting all text from the body container
        if len(valid_paragraphs) < 2 and article_body != soup:
             text_content = article_body.get_text(separator="\n", strip=True)
        else:
             text_content = "\n\n".join(valid_paragraphs)

        return {
            "url": url,
            "title": title,
            "published_date": published_date,
            "content": text_content,
            "raw_html_snippet": str(article_body)[:5000] # store truncated raw html for debugging/AI
        }
