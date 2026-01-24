from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime


class RSSFeed(BaseModel):
    """Represents a single feed entry from an RSS source."""
    title: str
    link: HttpUrl
    source: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None


class Article(BaseModel):
    """Represents a fetched and parsed news article."""
    title: str
    url: HttpUrl
    source: Optional[str] = None
    country: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None


class InputConfig(BaseModel):
    """Actor input config loaded from Apify input_schema.json."""
    source: str
    customFeedUrl: Optional[str] = None
    maxArticles: int = 20
    # useSummarization field is intentionally REMOVED
    region: str = Field("wt-wt", description="Region for search results.")
    timeLimit: str = Field("w", description="Time limit for search results.")
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass all external API calls.")


class SummaryResult(BaseModel):
    """Summarization output (LLM-generated)."""
    summary: str

# NEW MODEL to match the desired output format
class SnippetSource(BaseModel):
    """Represents a single source snippet used for grounding."""
    title: str
    url: HttpUrl
    source: str
    date: str # Date when the snippet was published/indexed


class DatasetRecord(BaseModel):
    """Final dataset record to push into Apify dataset."""
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = None
    # Summary now holds the LLM-generated summary or context
    summary: Optional[str] = Field(None, description="The LLM-generated summary or context used for analysis.") 
    
    # NEW FIELDS FOR ENHANCED VALUE (ADAPTED FOR WORLD NEWS)
    sentiment: Optional[str] = Field(None, description="Emotional/Urgency analysis result (High Urgency, Moderate, Low).")
    category: Optional[str] = Field(None, description="Primary news category (e.g., Politics, Conflict, Environment).")
    key_entities: Optional[List[str]] = Field(None, description="Key people, organizations, or locations mentioned.")
    
    # REMOVED: gdelt_tone (Global Markets specific metric)
    
    # NEW FIELD REQUIRED TO MATCH SUCCESSFUL OUTPUT
    snippet_sources: Optional[List[SnippetSource]] = Field(None, description="List of source snippets used for LLM grounding.")