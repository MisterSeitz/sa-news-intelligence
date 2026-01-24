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

    # Free model strategy list (Prioritized by user preference)
    FREE_MODEL_LIST = [
        "tngtech/deepseek-r1t2-chimera",
        "tngtech/deepseek-r1t-chimera",
        "z-ai/glm-4.5-air",
        "deepseek/deepseek-r1-0528",
        "tngtech/r1t-chimera",
        "qwen/qwen3-coder-480b-a35b-instruct",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemma-3-27b-it",
    ]

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Prefer OPENROUTER_API_KEY, fallback to OPENAI_API_KEY
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY/OPENAI_API_KEY is not set. Extraction will fail unless in test mode.")
        
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def analyze(self, article_data: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """
        Analyzes the article content to extract entities, incidents, and classification.
        Iterates through FREE_MODEL_LIST until successful.
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

        for model in self.FREE_MODEL_LIST:
            try:
                logger.info(f"Attempting extraction with model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert intelligence analyst for South Africa."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )

                result_text = response.choices[0].message.content.strip()
                # Some models might wrap JSON in markdown code blocks
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                
                return json.loads(result_text.strip())

            except APIError as e:
                logger.warning(f"Model {model} failed with API Error: {e}")
                continue # Try next model
            except json.JSONDecodeError:
                logger.warning(f"Model {model} failed to return valid JSON.")
                continue # Try next model
            except Exception as e:
                logger.warning(f"Model {model} failed with unexpected error: {e}")
                continue # Try next model

        logger.error("All free models failed extraction.")
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
