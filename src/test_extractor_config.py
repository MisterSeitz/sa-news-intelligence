
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.extractor import IntelligenceExtractor

class TestExtractorConfig(unittest.TestCase):
    
    def setUp(self):
        # Reset env vars for clean test
        if "ALIBABA_CLOUD_API_KEY" in os.environ:
            del os.environ["ALIBABA_CLOUD_API_KEY"]
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]

    @patch('src.extractor.OpenAI')
    def test_alibaba_coding_plan_config(self, mock_openai):
        """Test that Alibaba Client is initialized with Coding Plan URL and checks model list order."""
        os.environ["ALIBABA_CLOUD_API_KEY"] = "sk-test-ali"
        
        extractor = IntelligenceExtractor()
        
        # Check Base URL
        self.assertEqual(extractor.ali_url, "https://coding-intl.dashscope.aliyuncs.com/v1")
        
        # Check Model Priority
        self.assertEqual(extractor.ALIBABA_MODEL_LIST[0], "qwen3-coder-plus")
        
        # Check Plans Generation
        plans = extractor._get_provider_plans()
        
        # Expect 1 plan (Alibaba) since we didn't set OpenRouter key
        # But wait, code says "if self.fallback_client" it adds free fallback
        # Let's see if fallback client initializes without key? 
        # The constructor says: self.fallback_client = OpenAI(...) if self.fallback_key else None
        # So only Alibaba plan should be present
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]['client'], extractor.ali_client)
        self.assertEqual(plans[0]['models'][0], "qwen3-coder-plus")

    @patch('src.extractor.OpenAI')
    def test_fallback_logic(self, mock_openai):
        """Test that Free Models are always included as fallback."""
        os.environ["ALIBABA_CLOUD_API_KEY"] = "sk-test-ali"
        os.environ["OPENROUTER_API_KEY"] = "sk-test-router"
        
        extractor = IntelligenceExtractor()
        plans = extractor._get_provider_plans()
        
        # Should have 2 plans: Alibaba Primary, then OpenRouter Fallback
        self.assertEqual(len(plans), 2)
        
        # Plan 1: Alibaba
        self.assertEqual(plans[0]['client'], extractor.ali_client)
        
        # Plan 2: OpenRouter Free
        self.assertEqual(plans[1]['client'], extractor.fallback_client)
        self.assertTrue("google/gemini-2.0-flash-exp:free" in plans[1]['models'])
        self.assertTrue(":free" in plans[1]['models'][0])

    @patch('src.extractor.OpenAI')
    def test_prompt_generation(self, mock_openai):
        """Test that prompt includes new instructions for Tags and Categorization check."""
        extractor = IntelligenceExtractor()
        
        prompt = extractor._prepare_prompt(
            article_data={"title": "Ford Everest Review", "published_date": "2024-01-01"}, 
            content="Sample text", 
            category_hint="Business"
        )
        
        # Check for Critical Instructions
        self.assertIn('Verify the \'Category Hint\'', prompt)
        self.assertIn('tags', prompt)
        self.assertIn('change category to "Motoring"', prompt)

if __name__ == '__main__':
    unittest.main()
