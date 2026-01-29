from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any, Dict

class InputConfig(BaseModel):
    niche: str = "gaming"
    source: str = "all"
    customFeedUrl: Optional[str] = None
    maxArticles: int = 10
    region: str = "wt-wt"
    timeLimit: str = "w"
    discordWebhookUrl: Optional[str] = None
    enableBraveImageBackfill: bool = False
    forceRefresh: bool = False
    runTestMode: bool = False

class ArticleCandidate(BaseModel):
    title: str
    url: str
    source: str
    published: Optional[str] = None
    original_summary: Optional[str] = None
    niche: Optional[str] = None
    image_url: Optional[str] = None

class Incident(BaseModel):
    type: str = Field(description="Type of incident (e.g. Robbery, Protest)")
    description: str
    location: Optional[str] = None
    date: Optional[str] = None
    severity: int = Field(default=1, description="Severity 1-3")

class Person(BaseModel):
    name: str
    role: str = Field(description="Suspect, Victim, Official, etc.")
    status: Optional[str] = Field(description="Wanted, Arrested, Missing, etc.")
    details: Optional[str] = None

class Organization(BaseModel):
    name: str
    type: str = Field(description="Syndicate, Gang, Company, Govt")
    details: Optional[str] = None

class AnalysisResult(BaseModel):
    sentiment: str = Field(description="Hype/Interest level")
    category: str = Field(description="Thematic category")
    key_entities: List[str] = Field(description="Simple list of names for quick reference")
    summary: str = Field(description="AI synthesized summary")
    location: Optional[str] = Field(default=None, description="General location context")
    city: Optional[str] = Field(default=None, description="Specific city if mentioned")
    country: Optional[str] = Field(default=None, description="Country context")
    is_south_africa: bool = Field(default=False, description="True if content is relevant to South Africa")
    detected_niche: Optional[str] = Field(default=None, description="Re-routing hint")
    
    # Rich Intelligence (New)
    incidents: Optional[List[Incident]] = Field(default_factory=list)
    people: Optional[List[Person]] = Field(default_factory=list)
    organizations: Optional[List[Organization]] = Field(default_factory=list)
    
    # Niche Specific (Legacy/Compat)
    niche_data: Optional[Dict[str, Any]] = None # flexible dict for specific niche fields
    
    # Keeping flat fields for backward compat or easy access
    game_studio: Optional[str] = None
    game_genre: Optional[str] = None
    platform: Optional[List[str]] = None
    release_status: Optional[str] = None
    
    property_type: Optional[str] = None
    listing_price: Optional[str] = None
    sqft: Optional[str] = None
    market_status: Optional[str] = None

    company_name: Optional[str] = None
    round_type: Optional[str] = None
    funding_amount: Optional[str] = None
    investor_list: Optional[List[str]] = None

    token_symbol: Optional[str] = None
    market_trend: Optional[str] = None
    regulatory_impact: Optional[str] = None

    energy_type: Optional[str] = None
    infrastructure_project: Optional[str] = None
    capacity: Optional[str] = None
    status: Optional[str] = None

    # Motoring Specific
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_type: Optional[str] = None
    price_range: Optional[str] = None

class DatasetRecord(BaseModel):
    niche: str
    source_feed: str
    title: str
    url: str
    image_url: Optional[str] = None
    published: Optional[str]
    method: str = Field(description="Extraction method: 'scraped' or 'search_fallback'")
    sentiment: str
    category: str
    key_entities: List[str]
    ai_summary: str
    location: Optional[str]
    city: Optional[str]
    country: Optional[str]
    is_south_africa: bool
    raw_context_source: Optional[str] = None

    # Niche Specific (Optional)
    game_studio: Optional[str] = None
    game_genre: Optional[str] = None
    platform: Optional[List[str]] = None
    release_status: Optional[str] = None

    property_type: Optional[str] = None
    listing_price: Optional[str] = None
    sqft: Optional[str] = None
    market_status: Optional[str] = None

    company_name: Optional[str] = None
    round_type: Optional[str] = None
    funding_amount: Optional[str] = None
    investor_list: Optional[List[str]] = None

    token_symbol: Optional[str] = None
    market_trend: Optional[str] = None
    regulatory_impact: Optional[str] = None

    energy_type: Optional[str] = None
    infrastructure_project: Optional[str] = None
    capacity: Optional[str] = None
    status: Optional[str] = None

    # Motoring Specific
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_type: Optional[str] = None
    price_range: Optional[str] = None