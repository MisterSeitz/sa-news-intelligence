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

    # Alibaba Cloud Qwen models (Prioritized by capability then cost)
    ALIBABA_MODEL_LIST = [
        "qwen-flash",          # Seamless thinking/non-thinking, 1M context
        "qwen3-coder-flash",   # Strong code/JSON geneation
        "qwen-mt-flash",       # Fast, cost-effective
        "qwen-mt-plus",        # High quality fallback
        "qwen-mt-lite",        # Cheapest fallback
    ]

    # Free model strategy list (Prioritized by user preference)
    FREE_MODEL_LIST = [
        "meta-llama/llama-3.3-70b-instruct",  # Robust generalist
        "google/gemma-3-27b-it",              # Good structured output
        "tngtech/deepseek-r1t2-chimera",      # Strongest reasoning (671B)
        "deepseek/deepseek-r1-0528",          # Strong reasoning
        "z-ai/glm-4.5-air",                   # Agentic/Thinking capability
        "tngtech/deepseek-r1t-chimera",       # Balanced efficiency
        "qwen/qwen3-coder-480b-a35b-instruct",# Good at JSON/Structure
        "tngtech/r1t-chimera",                # Creative/Storytelling (Last resort)
    ]

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # Detect Provider
        self.is_alibaba = False
        
        self.api_key = api_key
        self.base_url = base_url
        
        if not self.api_key:
             if os.getenv("ALIBABA_CLOUD_API_KEY"):
                 self.api_key = os.getenv("ALIBABA_CLOUD_API_KEY")
                 self.is_alibaba = True
                 # Default to International endpoint (Singapore)
                 self.base_url = self.base_url or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
             elif os.getenv("OPENROUTER_API_KEY"):
                 self.api_key = os.getenv("OPENROUTER_API_KEY")
                 self.base_url = self.base_url or "https://openrouter.ai/api/v1"
             else:
                 self.api_key = os.getenv("OPENAI_API_KEY")
                 self.base_url = self.base_url or "https://openrouter.ai/api/v1" # Default fallback
        
        if not self.api_key:
            logger.warning("No API Key found (ALIBABA/OPENROUTER/OPENAI). Extraction will fail unless in test mode.")
        
        try:
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                logger.info(f"Initialized LLM Client. Alibaba: {self.is_alibaba}, Base: {self.base_url}")
            else:
                self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def analyze(self, article_data: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """
        Analyzes the article content to extract entities, incidents, and classification.
        Iterates through configured models until successful.
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
        2. **category**: General category (e.g. "Politics", "Crime", "Business").
        3. **niche_category**: ONE of ["Sports", "Politics", "Real Estate", "Gaming", "FoodTech", "Web3", "VC", "Cybersecurity", "Health", "Markets", "General"].
        4. **summary**: A concise 1-paragraph summary.
        5. **entities**: List of KEY people and organizations (max 8). 
           Format: {{"name": "...", "type": "Politician"|"Athlete"|"Businessperson"|"Civilian"|"Organization"|"Company"|"GovernmentBody"}}
           IMPORTANT: Do NOT include cities, countries, or physical locations here (e.g. "Johannesburg"). Use the 'locations' field for those. Only include "GovernmentBody" if it refers to the administration (e.g. "City of Johannesburg").
        6. **incidents**: If a crime/disaster/protest occurred, describe it. Format: {{"type": "...", "date": "...", "description": "..."}} (or null).
        7. **locations**: A list of specific physical locations mentioned (e.g. "Cape Town", "Sandton", "N1 Highway").
        
        JSON OUTPUT ONLY.
        """

        # Determine model list
        custom_model = os.getenv("LLM_MODEL")
        if custom_model:
             models_to_try = [custom_model]
             logger.info(f"Using custom model from env: {custom_model}")
        elif self.is_alibaba:
             models_to_try = self.ALIBABA_MODEL_LIST
             logger.info(f"Using Alibaba Cloud fallback list.")
        else:
             models_to_try = self.FREE_MODEL_LIST
             logger.info(f"Using OpenRouter free fallback list.")

        for model in models_to_try:
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
                # Handle Quota/Payment errors specifically
                if e.code == "402" or "credits" in str(e).lower() or "payment" in str(e).lower() or e.status_code == 429:
                     logger.warning(f"Model {model} hit Payment/Quota limit: {e}")
                else:
                     logger.warning(f"Model {model} failed with API Error: {e}")
                continue # Try next model
            except json.JSONDecodeError:
                logger.warning(f"Model {model} failed to return valid JSON.")
                continue # Try next model
            except Exception as e:
                logger.warning(f"Model {model} failed with unexpected error: {e}")
                continue # Try next model

        logger.error(f"All models failed extraction. (Using Alibaba: {self.is_alibaba})")
        return {}

    def _get_mock_data(self) -> Dict[str, Any]:
        return {
            "sentiment": "Moderate Urgency",
            "category": "Crime/Safety",
            "niche_category": "General",
            "summary": "Mock summary of a reported incident.",
            "entities": [{"name": "John Doe", "type": "Civilian"}],
            "incidents": {"type": "Robbery", "date": "2025-01-01", "description": "Mock robbery"},
            "locations": ["Johannesburg"]
        }
