"""Domain models for Zomato AI Restaurant Recommendation System."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class BudgetBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Restaurant(BaseModel):
    """Canonical catalog row representing a restaurant."""
    id: str
    name: str
    location: str
    cuisine: str
    cost: float
    rating: float
    votes: int = 0
    address: Optional[str] = None
    online_order: Optional[str] = None
    table_booking: Optional[str] = None
    rest_type: Optional[str] = None


class UserPreference(BaseModel):
    """User preferences submitted for recommendation."""
    location: str = Field(..., min_length=1, description="Target city or locality (e.g. Bangalore, Banashankari, Indiranagar)")
    budget: BudgetBand = Field(..., description="Budget tier: low, medium, or high")
    cuisine: str = Field(..., min_length=1, description="Desired cuisine (e.g. Italian, North Indian, Chinese)")
    min_rating: float = Field(default=3.5, ge=0.0, le=5.0, description="Minimum numeric rating threshold (0 to 5)")
    additional_preferences: Optional[str] = Field(default="", description="Free-text preferences, e.g. 'family-friendly, quick service, rooftop'")

    @field_validator("location", "cuisine", mode="before")
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be blank")
        return v


class Candidate(BaseModel):
    """Candidate restaurant sent to the LLM ranking engine."""
    id: str
    name: str
    location: str
    cuisine: str
    cost: float
    rating: float
    votes: int = 0
    table_booking: Optional[str] = None
    online_order: Optional[str] = None
    rest_type: Optional[str] = None


class Recommendation(BaseModel):
    """Output recommendation displayed to the user."""
    id: str
    name: str
    cuisine: str
    rating: float
    estimated_cost: float
    explanation: str
    rank: int


class RecommendationResponse(BaseModel):
    """Full recommendation response payload."""
    recommendations: List[Recommendation] = []
    summary: Optional[str] = None
    message: Optional[str] = None
    candidate_count: int = 0
