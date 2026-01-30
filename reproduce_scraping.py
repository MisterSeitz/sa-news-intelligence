
from bs4 import BeautifulSoup
import re

def _get_domain_specific_content(soup, url):
    # Copy of existing logic
    try:
        if "citizen.co.za" in url:
            content_div = soup.find('div', class_='single-content')
            if content_div:
                for junk in content_div.select('.related-posts-container, .teads-adCall, .read-more-posts-container, script, iframe'):
                    junk.decompose()
                return content_div.get_text(separator=' ', strip=True)
                
        elif "news24.com" in url:
             content_div = soup.find('div', class_='article__body')
             if content_div:
                for junk in content_div.select('.adslot-container, .newsletter-signup--group, .related-links, script, iframe'):
                    junk.decompose()
                return content_div.get_text(separator=' ', strip=True)
                
    except Exception as e:
        print(f"Domain specific scrape failed for {url}: {e}")
    return None

def test_scraping(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    url = "https://www.news24.com/sample"

    # 1. Image logic (simplified)
    image_url = None
    og_image = soup.find('meta', property='og:image')
    if og_image:
        image_url = og_image.get('content')
    print(f"Image URL: {image_url}")

    # 2. Text Content Logic
    text = _get_domain_specific_content(soup, url)
    
    if not text:
        # Heuristics
        article_body = soup.find('article') or soup.find('main') or soup.find(class_=re.compile(r'content|post|article'))
        
        if article_body:
            print(f"Found article body using selector: {article_body.name}, class: {article_body.get('class')}")
            # print first 100 chars
            print(f"Body snippet: {article_body.get_text(separator=' ', strip=True)[:100]}")
            text = article_body.get_text(separator=' ', strip=True)
        else:
            print("Fallback to soup.get_text")
            text = soup.get_text(separator=' ', strip=True)

    clean_text = re.sub(r'\s+', ' ', text).strip()
    print(f"Total Text Length: {len(clean_text)}")
    print(f"Final Text Snippet: {clean_text[:200]}")

if __name__ == "__main__":
    test_scraping(r"c:\Users\Administrator\Documents\Workspaces\actors\intelligence\sa-news-intelligence\sample\AGOA vote expected within days – but the impact on SA now deemed ‘modest’ _ News24.html")
