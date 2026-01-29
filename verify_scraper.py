import os
import asyncio
from src.services.scraper import scrape_article_content
from src.services.search import find_relevant_image

# Mock Actor log
class MockLog:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERR] {msg}")

import src.services.scraper
src.services.scraper.Actor = type('Actor', (), {'log': MockLog()})
import src.services.search
src.services.search.Actor = type('Actor', (), {'log': MockLog()})

def test_scraper():
    print("\n--- Testing Scraper ---")
    # Use a known article or a safe one. The Verge is usually good.
    url = "https://www.theverge.com/2024/1/1/24021234/test-article" 
    # Actually, let's use a real URL if we want to test parsing, 
    # but for structure we can use a dummy URL that will fail network but pass logic if we mock requests?
    # Or just use the Test Mode = True
    
    print("1. Testing Test Mode...")
    content, img = scrape_article_content("http://foo.bar", run_test_mode=True)
    print(f"Content: {content}")
    print(f"Image: {img}")
    assert img == "https://placehold.co/600x400/png"
    print("✅ Test Mode Passed")

    # If we could run real mode, we would.
    # But without assuming internet access or valid headers/cookies for specific sites, 
    # we might just rely on Test Mode for the plumbing.

def test_brave_backfill():
    print("\n--- Testing Brave Backfill (Test Mode) ---")
    img = find_relevant_image("Test Query", run_test_mode=True)
    print(f"Brave Image: {img}")
    assert "placehold.co" in img
    print("✅ Brave Test Mode Passed")

if __name__ == "__main__":
    test_scraper()
    test_brave_backfill()
