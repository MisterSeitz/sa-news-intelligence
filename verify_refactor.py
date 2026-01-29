import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Mock env vars
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock_key"
os.environ["ALIBABA_CLOUD_API_KEY"] = "mock_key"

async def test_imports():
    print("Testing Imports...")
    try:
        from src.models import AnalysisResult, Incident
        from src.services.ingestor import SupabaseIngestor
        from src.services.llm import analyze_content
        from src.services.feeds import NICHE_FEED_MAP
        print("[OK] Imports successful.")
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return

async def test_models():
    print("\nTesting Models...")
    try:
        from src.models import AnalysisResult, Incident
        
        inc = Incident(type="Robbery", description="Test", severity=2)
        ar = AnalysisResult(
            sentiment="High",
            category="Crime",
            key_entities=["Gang"],
            summary="Test summary",
            is_south_africa=True,
            incidents=[inc]
        )
        print(f"[OK] Model validation successful: {ar.incidents[0].type}")
    except Exception as e:
        print(f"[FAIL] Model validation failed: {e}")

async def test_ingestor():
    print("\nTesting Ingestor Logic (Mocked)...")
    try:
        from src.services.ingestor import SupabaseIngestor
        from src.models import AnalysisResult, ArticleCandidate, Incident
        
        ingestor = SupabaseIngestor()
        ingestor.supabase = MagicMock()
        
        # Test Data
        inc = Incident(type="Robbery", description="Armed robbery", severity=3)
        analysis = AnalysisResult(
            sentiment="High Urgency",
            category="Crime",
            key_entities=["Suspect A"],
            summary="A robbery occurred.",
            is_south_africa=True,
            incidents=[inc],
            location="Johannesburg"
        )
        article = ArticleCandidate(
            url="http://test.com/crime",
            title="crime report",
            source="test",
            published="2023-01-01"
        )
        
        await ingestor.ingest(analysis, article)
        
        print("[OK] Ingestor ran without errors.")
        
    except Exception as e:
        print(f"[FAIL] Ingestor failed: {e}")

async def main():
    await test_imports()
    await test_models()
    await test_ingestor()

if __name__ == "__main__":
    asyncio.run(main())
