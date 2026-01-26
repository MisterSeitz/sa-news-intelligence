import asyncio
import logging
from search_client import BraveSearchClient
from scraper import NewsScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_client():
    logger.info("🧪 Testing BraveSearchClient...")
    client = BraveSearchClient()
    
    # Test Web Search
    logger.info("   Testing Web Search...")
    results = await client.search("South Africa News", count=1)
    if results:
        logger.info(f"   ✅ Web Search Result: {results[0].get('title')}")
    else:
        logger.warning("   ⚠️ Web Search returned no results (check API quotas).")

    # Test Image Search
    logger.info("   Testing Image Search...")
    images = await client.search_images("Table Mountain", count=1)
    if images:
        logger.info(f"   ✅ Image Search Result: {images[0].get('thumbnail', {}).get('src') or images[0].get('url')}")
    else:
        logger.warning("   ⚠️ Image Search returned no results.")

def test_scraper_fallback():
    logger.info("🧪 Testing Scraper Image Fallback...")
    scraper = NewsScraper()
    
    # HTML with NO OG:Image but with a body image
    html_content = """
    <html>
        <head>
            <meta property="og:title" content="Test Article" />
        </head>
        <body>
            <div class="article-body">
                <p>Some text here.</p>
                <img src="https://example.com/body-image.jpg" width="600" />
                <p>More text.</p>
            </div>
        </body>
    </html>
    """
    
    logger.info("   Parsing HTML snippet...")
    data = scraper._extract_content(html_content, "https://example.com/article")
    
    image_url = data.get("image_url")
    if image_url == "https://example.com/body-image.jpg":
        logger.info(f"   ✅ Scraper correctly extracted fallback image: {image_url}")
    else:
        logger.error(f"   ❌ Scraper failed to extract fallback image. Got: {image_url}")

async def main():
    await test_search_client()
    test_scraper_fallback()

if __name__ == "__main__":
    asyncio.run(main())
