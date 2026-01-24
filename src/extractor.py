import os
import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI, APIError

# Configure logging
logger = logging.getLogger(__name__)

class IntelligenceExtractor:
    """
    Extracts structured intelligence (People, Crimes, Locations, Classification) 
    from news article text using an LLM via OpenRouter.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY is not set. Extraction will fail unless in test mode.")
        
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def analyze(self, article_data: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """
        Analyzes the article content to extract entities, incidents, and classification.
        """
        if test_mode:
            logger.info("TEST MODE: returning mock extraction data.")
            return self._get_mock_data()

        if not self.client:
            logger.error("Client not initialized. Returning empty analysis.")
            return {}

        content = article_data.get("content", "")
        if len(content) < 100:
            logger.warning(f"Content too short for analysis ({len(content)} chars). Skipping.")
            return {}

        # Limit content to avoid context window issues/costs (approx 4000 tokens)
        truncated_content = content[:12000]

        prompt = f"""
        Analyze the following news article text and extract structured intelligence for a South African civic database.
        
        Article: "{article_data.get('title', 'Unknown')}"
        Date: "{article_data.get('published_date', 'Unknown')}"
        Content: "{truncated_content}"

        Extract the following fields into a valid JSON object:
        1. **sentiment**: "High Urgency", "Moderate Urgency", or "Low Urgency".
        2. **category**: "Politics/Government", "Crime/Safety", "Environment", "Economy", "Social", "Other".
        3. **summary**: A concise 1-paragraph summary.
        4. **entities**: List of KEY people and organizations mentioned (max 5). Format: {{"name": "...", "type": "Person"|"Organization"}}
        5. **incidents**: If a crime/disaster/protest occurred, describe it. Format: {{"type": "...", "date": "...", "description": "..."}} (or null).
        6. **locations**: A list of specific physical locations mentioned (e.g. "Cape Town", "Sandton", "N1 Highway").
        
        JSON OUTPUT ONLY.
        """

        try:
            response = self.client.chat.completions.create(
                model="google/gemini-2.0-flash-001", # Cost effective robust model on OpenRouter
                messages=[
                    {"role": "system", "content": "You are an expert intelligence analyst for South Africa."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )

            result_text = response.choices[0].message.content.strip()
            return json.loads(result_text)

        except APIError as e:
            logger.error(f"LLM API Error: {e}")
            return {}
        except json.JSONDecodeError:
            logger.error("Failed to decode LLM response as JSON.")
            return {}
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {}

    def _get_mock_data(self) -> Dict[str, Any]:
        return {
            "sentiment": "Moderate Urgency",
            "category": "Crime/Safety",
            "summary": "Mock summary of a reported incident.",
            "entities": [{"name": "John Doe", "type": "Person"}],
            "incidents": {"type": "Robbery", "date": "2025-01-01", "description": "Mock robbery"},
            "locations": ["Johannesburg"]
        }
