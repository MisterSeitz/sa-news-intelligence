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
        "qwen3-coder-plus",    # Latest Qwen3 Coding Specialist
        "qwen-coder-plus",     # Qwen2.5 Coding Specialist
        "qwen-plus",           # Good balance of speed and quality
        "qwen-turbo",          # Fast, cost-effective
        "qwen-max",            # High intelligence
        "qwen-long",           # Long context fallback
    ]

    # Free/OpenRouter model strategy list (Prioritized by user preference)
    FREE_MODEL_LIST = [
        "qwen/qwen3-coder-480b-a35b-instruct",# Qwen3 on OpenRouter
        "meta-llama/llama-3.3-70b-instruct",  # Robust generalist
        "google/gemma-3-27b-it",              # Good structured output
        "deepseek/deepseek-r1-0528",          # Strong reasoning
        "z-ai/glm-4.5-air",                   # Agentic/Thinking capability
    ]

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """
        Initializes with support for multiple providers (Alibaba and OpenRouter).
        """
        self.model_override = model
        
        # 1. Alibaba Setup
        self.ali_key = os.getenv("ALIBABA_CLOUD_API_KEY")
        self.ali_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        self.ali_client = OpenAI(api_key=self.ali_key, base_url=self.ali_url) if self.ali_key else None
        
        # 2. OpenRouter/Fallback Setup
        self.fallback_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.fallback_url = "https://openrouter.ai/api/v1"
        self.fallback_client = OpenAI(api_key=self.fallback_key, base_url=self.fallback_url) if self.fallback_key else None
        
        # Priority Flags
        self.is_alibaba_primary = bool(self.ali_key)
        
        if not self.ali_key and not self.fallback_key:
            logger.warning("No API Keys found (ALIBABA/OPENROUTER/OPENAI). Extraction will fail.")
        
        logger.info(f"Initialized Extractor. Alibaba Available: {bool(self.ali_key)}, OpenRouter Available: {bool(self.fallback_key)}")

    def _get_provider_plans(self) -> List[Dict[str, Any]]:
        """
        Returns a list of (client, model_list) pairs to try in order.
        """
        plans = []
        
        # Handle specific model override
        if self.model_override:
            # Detect which provider the override belongs to
            if "qwen3-coder" in self.model_override or "qwen-coder" in self.model_override or self.model_override.startswith("qwen-"):
                if self.ali_client: plans.append({"client": self.ali_client, "models": [self.model_override]})
                if self.fallback_client: plans.append({"client": self.fallback_client, "models": [f"qwen/{self.model_override}" if "/" not in self.model_override else self.model_override]})
            else:
                if self.fallback_client: plans.append({"client": self.fallback_client, "models": [self.model_override]})
            return plans

        # Standard Fallback logic: Try Primary then Secondary
        if self.is_alibaba_primary:
            if self.ali_client: plans.append({"client": self.ali_client, "models": self.ALIBABA_MODEL_LIST})
            if self.fallback_client: plans.append({"client": self.fallback_client, "models": self.FREE_MODEL_LIST})
        else:
            if self.fallback_client: plans.append({"client": self.fallback_client, "models": self.FREE_MODEL_LIST})
            if self.ali_client: plans.append({"client": self.ali_client, "models": self.ALIBABA_MODEL_LIST})
            
        return plans

    def _prepare_prompt(self, article_data: Dict[str, Any], content: str, category_hint: str) -> str:
        """Constructs the prompt with niche-specific instructions."""
        base_prompt = f"""
        Analyze the following news article text and extract structured intelligence for a South African civic database.
        
        Article: "{article_data.get('title', 'Unknown')}"
        Date: "{article_data.get('published_date', 'Unknown')}"
        Content: "{content}"
        
        Category Hint: {category_hint}
        """

        # Define specialized requirements based on category
        specific_instructions = ""
        
        if "Crime" in category_hint or "Courts" in category_hint:
             specific_instructions = """
             **CRIME INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "incident_type": Specific crime (e.g. "Armed Robbery", "Fraud", "Poaching")
             - "weapon": Weapon used if mentioned (e.g. "9mm pistol", "AK47", "Knife")
             - "suspects_count": Integer estimation
             - "station": SAPS Station mentioned (e.g. "Hillbrow SAPS")
             - "case_number": CAS number if available
             - "courts": Court names mentioned
             """
             
        elif "Politics" in category_hint or "Government" in category_hint or "Election" in category_hint:
             specific_instructions = """
             **POLITICAL & ELECTION INTELLIGENCE MODE (2026 ELECTIONS focus)**
             Extract the following into a 'niche_data' object:
             - "politicians": List of politician names involved
             - "mentioned_candidates": List of specific election candidates
             - "mentioned_parties": List of political parties involved (ANC, DA, EFF, MK, PA, etc.)
             - "ward_codes": List of Ward codes if mentioned (Format: "Ward 123" -> 123, or specific codes like "19100054")
             - "municipality_codes": List of Municipalities (e.g. "City of Cape Town", "Ethekwini", "Tshwane")
             - "policy_areas": List of policy topics (e.g. "NHI", "Land Reform", "Service Delivery", "Water Crisis")
             - "corruption_risk": Boolean (True if corruption/fraud/irregularity allegated)
             - "election_event": Boolean (True if about campaigning, voting, registration, or results)
             """

        elif "Business" in category_hint or "Economy" in category_hint or "Markets" in category_hint:
             specific_instructions = """
             **BUSINESS INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "companies": List of company names
             - "tickers": Stock tickers if public (e.g. "JSE:NPN")
             - "deal_value_zar": Monetary value involved (estimate numeric)
             - "sector": Industry sector
             - "market_sentiment": "Bullish" | "Bearish" | "Neutral"
             """

        elif "Health" in category_hint:
             specific_instructions = """
             **HEALTH INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "disease": Disease or condition mentioned
             - "outbreak_location": Specific area of outbreak
             - "hospital_status": Status of facilities
             - "stats": Key statistics (cases, deaths, recoveries)
             """
             
        elif "Sport" in category_hint:
             specific_instructions = """
             **SPORTS INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "sport": Sport name (Rugby, Cricket, Soccer)
             - "teams": Teams involved
             - "match_result": Score or outcome if applicable.
             - "key_players": Players mentioned
             """

        elif "Motoring" in category_hint or "Automotive" in category_hint or "Cars" in category_hint:
             specific_instructions = """
             **MOTORING INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "brand": Primary automotive brand (Standardize: Toyota, VW, BMW, etc.)
             - "model": Specific model mentioned (e.g. "Polo Vivo", "Ranger")
             - "subniche": "EV" | "Used Market" | "OEM" | "General"
             - "price_mentioned": Numeric value if available
             - "launch_date": If new car launch
             """

        elif "Energy" in category_hint or "Power" in category_hint or "Nuclear" in category_hint:
             specific_instructions = """
             **ENERGY & NUCLEAR INTELLIGENCE MODE**
             Determine if this is "Nuclear" specific or "General Energy".
             
             If NUCLEAR (Keywords: Koeberg, Rosatom, Westinghouse, SMR, Thyspunt, NNR):
             Extract into 'niche_data':
             - "energy_table": "nuclear_energy"
             - "technology": "SMR" | "PWR" | "Large React" | "General"
             - "status": "Planned" | "Operational" | "Decommissioned" | "Construction"
             - "target_year": Year mentioned for completion/shut down
             - "capacity_mw": Numeric MW
             
             If GENERAL ENERGY (Grid, Renewables, Coal, Storage):
             Extract into 'niche_data':
             - "energy_table": "energy"
             - "subniche": "Grid" | "Renewables" | "Storage" | "Hydrogen" | "Policy" | "Market Pricing"
             - "project_name": Name of project/plant
             - "location": Location
             - "capacity_mw": Numeric MW
             """

        elif "Semiconductor" in category_hint or "Chip" in category_hint:
             specific_instructions = """
             **SEMICONDUCTOR INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "company": Chip manufacturer/designer
             - "chip_type": "GPU" | "CPU" | "Memory" | "Automotive"
             - "application": "AI" | "Consumer" | "Industrial"
             """

        elif "Logistics" in category_hint or "Supply Chain" in category_hint:
             specific_instructions = """
             **LOGISTICS INTELLIGENCE MODE**
             Extract the following into a 'niche_data' object:
             - "transport_mode": "Sea" | "Air" | "Rail" | "Road"
             - "route": Origin -> Destination
             - "company": Logistics provider
             - "disruption_status": "Normal" | "Delayed" | "Blocked"
             """

        elif "Climate" in category_hint or "Green" in category_hint:
             specific_instructions = """
             **CLIMATE TECH MODE**
             Extract the following into a 'niche_data' object:
             - "technology": Specific tech (e.g. "Carbon Capture", "Green Hydrogen")
             - "investment_round": "Seed" | "Series A" | "Grant" if applicable
             - "impact_metric": CO2 reduction or similar metric
             """

        return base_prompt + f"""
        Extract the following fields into a valid JSON object:
        1. **sentiment**: "High Urgency", "Moderate Urgency", or "Low Urgency".
        2. **category**: General category (e.g. "Politics", "Crime", "Business").
        3. **niche_category**: ONE of ["Sports", "Politics", "Real Estate", "Gaming", "FoodTech", "Web3", "VC", "Cybersecurity", "Health", "Markets", "General", "Crime", "Motoring", "Energy", "Semiconductors", "Logistics", "ClimateTech"].
        4. **summary**: A concise 1-paragraph summary.
        5. **entities**: List of KEY people and organizations (max 8). 
           Format: {{"name": "...", "type": "Politician"|"Athlete"|"Businessperson"|"Civilian"|"Organization"|"Company"|"GovernmentBody"}}
        6. **locations**: A list of specific physical locations mentioned (e.g. "Cape Town", "Sandton", "N1 Highway").
        7. **niche_data**: {{
            {specific_instructions if specific_instructions else "Generic metadata relevant to the article."}
        }}
        
        JSON OUTPUT ONLY.
        """

    def analyze(self, article_data: Dict[str, Any], content_text: str = "", test_mode: bool = False) -> Dict[str, Any]:
        """
        Analyzes article content with automatic provider failover.
        """
        if test_mode:
            return self._get_mock_data()

        content = content_text or article_data.get("content", "")
        if not content or len(content) < 100:
            logger.warning("Content too short for analysis.")
            return {}

        truncated_content = content[:12000]
        category_hint = article_data.get("csv_category", "General")
        
        # Prepare Prompt
        prompt = self._prepare_prompt(article_data, truncated_content, category_hint)
        
        # Try Plans
        plans = self._get_provider_plans()
        
        for plan in plans:
            client = plan["client"]
            models = plan["models"]
            
            for model_name in models:
                logger.info(f"🧠 Attempting extraction with model: {model_name}")
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are an expert intelligence analyst for South Africa. Return valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                        timeout=60.0 # Aggressive timeout for reliability
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                    # Clean markdown
                    if result_text.startswith("```json"): result_text = result_text[7:]
                    if result_text.endswith("```"): result_text = result_text[:-3]
                    
                    analysis = json.loads(result_text.strip())
                    if "title" in analysis or "category" in analysis:
                        logger.info(f"✅ Successful extraction using {model_name}")
                        return analysis
                        
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    # Switch provider on Auth error (401)
                    if "401" in str(e) or "Unauthorized" in str(e):
                        logger.error(f"❌ Auth error on {model_name}. Switching provider...")
                        break 
                    continue
                    
        logger.error("All extraction attempts failed.")
        return {}

    def analyze_crime_snippet(self, snippet: str, query_context: str) -> Dict[str, Any]:
        """
        Specialized extraction for short search result snippets with failover.
        """
        prompt = f"""
        Analyze this search result snippet about '{query_context}' in South Africa.
        Snippet: "{snippet}"

        Determine if this describes a:
        1. "Incident" (Crime happening)
        2. "Wanted" (Police looking for suspect)
        3. "Missing" (Missing person report)
        4. "Syndicate" (Organized crime group info)
        5. "Irrelevant" (Not a crime, or NOT in South Africa)

        CRITICAL LOCATION CHECK:
        - If the event is NOT in South Africa, return "Irrelevant". 
        - Watch for ambiguous names.
        - Hints for SA Context: SAPS, Rand, Provinces, Local terms.

        JSON OUTPUT ONLY. Format:
        {{
            "type": "Incident" | "Wanted" | "Missing" | "Syndicate" | "Irrelevant",
            "data": {{ ... }}
        }}
        """

        plans = self._get_provider_plans()
        for plan in plans:
            client = plan["client"]
            models = plan["models"]
            # For snippets, we can just try the first 2 models to keep it fast
            for model_name in models[:2]:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        timeout=15.0
                    )
                    return json.loads(response.choices[0].message.content.strip())
                except:
                    continue
        return {"type": "Irrelevant", "data": {}}

    def generate_briefing_script(self, stories: List[Dict]) -> Dict[str, str]:

    def generate_briefing_script(self, stories: List[Dict]) -> Dict[str, str]:
        """
        Generates a 3-part script for HeyGen video based on input stories.
        Strictly enforces word count limits.
        """
        if not self.client: return {}
        
        # Prepare context
        story_text = ""
        for i, s in enumerate(stories):
            story_text += f"Story {i+1}: {s.get('title')} - {s.get('summary')}\n"

        prompt = f"""
        You are a Morning News Anchor scriptwriter. Write a script for a 60-second video update (approx 120 words MAX TOTAL).
        
        Input Stories:
        {story_text}
        
        Requirements:
        1. **Slide 1 (Intro + Story 1)**: Catchy welcome, then cover the most important story.
        2. **Slide 2 (Story 2 & 3)**: Briefly cover the next two stories.
        3. **Slide 3 (Outro)**: Quick wrap up and "Stay safe, South Africa".
        
        Tone: Professional, energetic, South African context.
        Output: JSON with keys "slide_1", "slide_2", "slide_3".
        NO MARKDOWN. JUST JSON.
        """
        
        models = self._get_models()
        for model in models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional news scriptwriter."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                
                content = response.choices[0].message.content.strip()
                if content.startswith("```json"): content = content[7:]
                if content.endswith("```"): content = content[:-3]
                
                return json.loads(content.strip())
            except Exception as e:
                logger.warning(f"Script generation failed on {model}: {e}")
                continue
                
        return {}

    def analyze_deep_intelligence(self, text: str, source_url: str) -> Dict[str, Any]:
        """
        Performs deep analysis on full article text to extract multiple entities and incidents.
        Enforces strict South African context.
        """
        if not self.client: return {}
        
        # Limit text
        truncated_text = text[:15000]

        prompt = f"""
        Analyze the following full text from a news source ({source_url}).
        
        CRITICAL GOAL: Extract structured intelligence for a South African Crime & News Database.
        
        CONTEXT CHECK:
        - Only extract events/entities RELEVANT to South Africa.
        - If the text is about a foreign event (e.g. shooting in USA), return {{"relevant": false}}.

        TEXT:
        "{truncated_text}"

        EXTRACT THE FOLLOWING (JSON ONLY):
        1. "relevant": boolean (Is this South African?)
        2. "sentiment": "High Urgency" | "Moderate Urgency" | "Low Urgency"
        3. "summary": One paragraph summary.
        4. "incidents": List of distinct crime/disaster events. 
           Format: {{ "type": "...", "description": "...", "date": "...", "location": "...", "severity": 1-3 }}
        5. "people": List of key individuals (Suspects, Victims, Officials).
           Format: {{ "name": "...", "role": "Suspect"|"Victim"|"Official"|"Civilian", "status": "Wanted"|"Arrested"|"Deceased"|"Unknown", "details": "..." }}
        6. "organizations": List of groups (Syndicates, Gangs, Companies, Govt Depts).
           Format: {{ "name": "...", "type": "Syndicate"|"Gang"|"Company"|"Govt", "details": "..." }}
        
        OUTPUT JSON:
        """

        models_to_try = self._get_models()
        
        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a senior intelligence analyst for South Africa."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                result_text = response.choices[0].message.content.strip()
                if result_text.startswith("```json"): result_text = result_text[7:]
                if result_text.endswith("```"): result_text = result_text[:-3]
                
                data = json.loads(result_text.strip())
                if isinstance(data, dict):
                    return data
            except Exception as e:
                logger.warning(f"Deep extraction failed on {model}: {e}")
                continue
                
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

    def generate_briefing_script(self, stories: List[Dict]) -> Dict[str, Any]:
        """
        Generates a 30-60 second morning briefing script from a list of stories.
        """
        if not self.client or not stories: return {}
        
        # Prepare context
        stories_text = ""
        for i, s in enumerate(stories):
            stories_text += f"{i+1}. {s.get('title')} ({s.get('category')}): {s.get('summary')}\n"
            
        prompt = f"""
        You are a professional news anchor for 'Visita South Africa'.
        Write a concise, engaging Morning News Briefing script based on these top stories:
        
        {stories_text}
        
        CRITICAL CONSTRAINTS:
        1. **Time Limit**: The video MUST be under 60 seconds. Total word count MUST be under 120 words.
        2. **Structure**: Split into exactly 3 slides.
            - **Slide 1 (Intro + Top Story)**: "Good morning." + Brief summary of Story 1.
            - **Slide 2 (Rapid Fire)**: Very quick 1-sentence mentions of Story 2 and Story 3.
            - **Slide 3 (Conclusion)**: "That's your briefing. Stay safe."
            
        OUTPUT JSON ONLY:
        {{
            "slide_1": "Script for slide 1...",
            "slide_2": "Script for slide 2...",
            "slide_3": "Script for slide 3..."
        }}
        """



        models_to_try = self._get_models()
        
        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional news script writer."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                result_text = response.choices[0].message.content.strip()
                if result_text.startswith("```json"): result_text = result_text[7:]
                if result_text.endswith("```"): result_text = result_text[:-3]
                
                return json.loads(result_text)
            except Exception as e:
                logger.warning(f"Script generation failed on {model}: {e}")
                
        return {}

