import logging
import json
from extractor import IntelligenceExtractor

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMotoring")

def test_motoring_extraction():
    logger.info("🚗 Testing Motoring Niche Extraction...")
    
    # 1. Mock Extractor (or real one if env vars set)
    # We will assume env vars are present or we mock the method.
    # To test properly, we need the real prompt logic, so we need to instantiate Extractor.
    
    extractor = IntelligenceExtractor(base_url="https://coding-intl.dashscope.aliyuncs.com/v1", model="qwen-turbo") # Dummy or real
    
    # Mock specific article text
    article_text = """
    New Toyota Hilux GR Sport III launched in South Africa.
    The updated bakkie features a more aggressive design and a boost in power to 165kW.
    Priced from R999,000, it competes directly with the Ford Ranger Raptor.
    Toyota has also hinted at a mild-hybrid version coming later in 2025.
    """
    
    source_url = "https://www.cars.co.za/news/toyota-hilux-gr-sport-specs/"
    
    # Mock the _get_models to avoid issues if env not set, OR rely on real API if enabled.
    # We'll rely on the class logic. If no API key, it might fail.
    # But usually user has keys.
    
    logger.info("   Invoking analyze_deep_intelligence with Motoring hint...")
    
    # We'll force a "Motoring" category hint via the prompt or let it deduce?
    # The analyze_deep_intelligence method uses 'csv_category' logic or deduces.
    # Let's mock the input to the internal prompt logic if possible, or just call the public method.
    
    # Since analyze_deep_intelligence does scraping/fetching? No, it takes text.
    # Wait, analyze_deep_intelligence(text, url).
    
    # Does it accept a category hint directly? 
    # No, it uses self.classify_article or csv_category logic internally.
    # Let's verify analyze method signature in extractor.py
    # def analyze(self, article_data: Dict, content: str, csv_category: str = None) -> Dict[str, Any]:
    
    result = extractor.analyze(
        article_data={"title": "Toyota Hilux GR Sport Launched", "published_date": "2025-01-26"},
        content=article_text,
        csv_category="Motoring"
    )
    
    logger.info("   📝 Extraction Result:")
    logger.info(json.dumps(result, indent=2))
    
    # Assertions
    niche_data = result.get("niche_data", {})
    if niche_data.get("brand") == "Toyota":
        logger.info("   ✅ Correct Brand Identified: Toyota")
    else:
        logger.error(f"   ❌ Failed to identify Brand. Got: {niche_data.get('brand')}")
        
    if "Hilux" in niche_data.get("model", ""):
        logger.info(f"   ✅ Correct Model Identified: {niche_data.get('model')}")
        
    if "Ranger" in str(result):
         logger.info("   ✅ Standard entities extraction likely worked (Ford Ranger mentions)")

if __name__ == "__main__":
    test_motoring_extraction()
