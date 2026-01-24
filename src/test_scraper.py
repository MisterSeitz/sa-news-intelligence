import asyncio
import logging
from scraper import NewsScraper

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    test_urls = [
        "https://www.dailymaverick.co.za/section/maverick-news/", # Often has decent meta tags
        "https://www.news24.com/", # Often tricky dynamic content
        "https://iol.co.za/news/politics/"
    ]

    async with NewsScraper(headless=True) as scraper:
        for url in test_urls:
            print(f"\n--- Testing Crawl: {url} ---")
            links = await scraper.get_article_links(url, max_links=3)
            print(f"Found {len(links)} links: {links}")
            
            if links:
                article_url = links[0]
                print(f"--- Fetching First Article: {article_url} ---")
                result = await scraper.fetch_article(article_url)
                
                if "error" in result:
                    print(f"FAILED: {result['error']}")
                else:
                    print(f"Title: {result.get('title')}")
                    print(f"Date: {result.get('published_date')}")
                    content_preview = result.get('content', '')[:200].replace('\n', ' ')
                    print(f"Content Preview: {content_preview}...")
                    print(f"Raw HTML Size: {len(result.get('raw_html_snippet', ''))} chars")

if __name__ == "__main__":
    asyncio.run(main())
