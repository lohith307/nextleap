"""
Pydantic models for Executive Weekly Pulse Synthesis in Phase 3.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ThemePulseItem(BaseModel):
    """A single theme's summary in the weekly pulse."""
    theme_id: str
    theme_name: str
    percentage_share: float
    executive_summary: str
    selected_verbatim_quote: str
    action_idea: str


class WeeklyPulseReport(BaseModel):
    """Executive Weekly Customer Voice Pulse Report."""
    date_range: str
    total_reviews_analyzed: int
    top_themes: List[ThemePulseItem] = Field(default_factory=list)
    verbatim_quotes: List[str] = Field(default_factory=list)
    action_ideas: List[str] = Field(default_factory=list)
    weekly_pulse_markdown: str
    word_count: int = 0
    quote_veracity_verified: bool = False
    pii_free_verified: bool = False
    tokens_consumed: int = 0
    model_used: str = "llama-3.3-70b-versatile"

