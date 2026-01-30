import os
import json
from openai import OpenAI
from apify import Actor
from ..models import AnalysisResult, Incident
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

def _prepare_prompt(content: str, niche: str) -> str:
    """Constructs the prompt with specialized South African context instructions."""
    
    base_prompt = f"""
    Analyze the following news article text and extract structured intelligence for a South African civic database.
    
    Content: "{content[:12000]}"
    
    Context Niche: {niche}
    """

    specific_instructions = ""
    
    # Niche Logic (Ported from old Extractor)
    if niche in ["crime", "courts"]:
            specific_instructions = """
            **CRIME INTELLIGENCE MODE**
            Extract "incidents" list:
            - type: "Armed Robbery", "Murder", "Fraud", "Poaching", "Hijacking", "Corruption"
            - description: Brief details (weapon used, suspects count)
            - severity: 1 (Low), 2 (Medium), 3 (High/Critical)
            - location: Specific address/suburb
            
            Extract "people" list (Suspects/Wanted/Missing):
            - role: "Suspect", "Wanted", "Missing", "Victim", "Official"
            - status: "Wanted", "Arrested", "Deceased", "at large"
            """
            
    elif niche in ["politics", "government", "elections"]:
            specific_instructions = """
            **POLITICAL INTELLIGENCE MODE**
            Extract into 'niche_data' dict:
            - "politicians": List of names
            - "mentioned_parties": List of parties (ANC, DA, EFF, MK, PA, etc.)
            - "municipality": e.g. "City of Cape Town"
            - "corruption_risk": Boolean
            - "election_event": Boolean (voting, campaigning)
            """

    elif niche in ["business", "markets", "economy"]:
            specific_instructions = """
            **BUSINESS INTELLIGENCE MODE**
            Extract into 'niche_data':
            - "companies": List of company names
            - "tickers": JSE Tickers (e.g. JSE:NPN)
            - "deal_value_zar": Monetary value
            - "market_sentiment": "Bullish", "Bearish", "Neutral"
            """

    elif niche == "energy":
            specific_instructions = """
            **ENERGY INTELLIGENCE MODE**
            Extract into 'niche_data':
            - "energy_type": "Nuclear", "Solar", "Coal", "Grid"
            - "infrastructure_project": Name of plant/project
            - "status": "Planned", "Operational", "Load Shedding"
            """
            
    elif niche == "motoring":
            specific_instructions = """
            **MOTORING MODE**
            Extract into 'niche_data':
            - "vehicle_make": Brand
            - "vehicle_model": Model
            - "price_range": Price mentioned
            """

    return base_prompt + f"""
    {specific_instructions}

    MANDATORY JSON OUTPUT FORMAT (Matches AnalysisResult schema):
    {{
        "sentiment": "High Urgency" | "Moderate Urgency" | "Low Urgency",
        "category": "Thematic Category (Crime, Politics, Business, Sport, etc.)",
        "summary": "1 paragraph summary",
        "key_entities": ["List", "of", "names"],
        "location": "General Location",
        "city": "Specific City",
        "is_south_africa": boolean,
        "detected_niche": "crime" | "politics" | "business" | "sport" | "motoring" | "energy" | "general",
        
        "incidents": [
            {{ "type": "...", "description": "...", "location": "...", "date": "YYYY-MM-DD", "severity": 1-3 }}
        ],
        "people": [
            {{ "name": "...", "role": "...", "status": "...", "details": "..." }}
        ],
        "organizations": [
             {{ "name": "...", "type": "...", "details": "..." }}
        ],
        "niche_data": {{ ... specific fields ... }}
    }}
    
    JSON ONLY.
    """

def analyze_content(content: str, niche: str = "general", run_test_mode: bool = False) -> AnalysisResult:
    """
    Analyzes content using LLM to extract structured intelligence.
    """
    if run_test_mode:
        Actor.log.info("⚠️ AI Analysis running in TEST MODE (Mock Data returned).")
        # Return mock data
        return AnalysisResult(
            sentiment="Moderate Urgency",
            category="General News",
            key_entities=["Test Entity"],
            summary="This is a test summary for SA News.",
            location="Cape Town",
            city="Cape Town",
            country="South Africa",
            is_south_africa=True,
            incidents=[Incident(type="Test Incident", description="Mock test", location="Cape Town")]
        )

    api_key = os.getenv("ALIBABA_CLOUD_API_KEY")
    client = None
    
    # Provider Selection
    if api_key:
        client = OpenAI(
            base_url="https://coding-intl.dashscope.aliyuncs.com/v1",
            api_key=api_key,
        )
        model = "qwen3-coder-plus"
        Actor.log.info(f"🤖 Starting AI Analysis using Alibaba Qwen ({model})")
    else:
        # Fallback
        Actor.log.warning("⚠️ Alibaba Key missing. Using OpenRouter Fallback.")
        client = OpenAI(
             base_url="https://openrouter.ai/api/v1",
             api_key=os.getenv("OPENROUTER_API_KEY")
        )
        model = "google/gemini-2.0-flash-exp:free"
        Actor.log.info(f"🤖 Starting AI Analysis using OpenRouter ({model})")

    # Prompt
    prompt = _prepare_prompt(content, niche)
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior intelligence analyst for South Africa."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            timeout=90.0
        )
        
        result_text = completion.choices[0].message.content
        
        # Clean markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        data = json.loads(result_text)
        
        # Validate/Clean
        if "category" not in data: data["category"] = "General"
        
        Actor.log.info(f"✨ AI Analysis Complete. Sentiment: {data.get('sentiment')}")
        return AnalysisResult(**data)

    except Exception as e:
        Actor.log.error(f"Analysis failed: {e}")
        return AnalysisResult(
            sentiment="Error",
            category="Error",
            key_entities=[],
            summary=f"Analysis failed: {e}",
            is_south_africa=False
        )