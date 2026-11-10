"""
Pydantic models for Thematic Clustering in Phase 2.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from src.models.review import SanitizedReview


class ThemeDefinition(BaseModel):
    """Canonical taxonomy definition for a Zomato theme."""
    theme_id: str
    name: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    regex_patterns: List[str] = Field(default_factory=list)


class ThemeCluster(BaseModel):
    """Clustered group of reviews representing a customer voice theme."""
    theme_id: str
    name: str
    description: str
    review_count: int = 0
    percentage_share: float = 0.0
    negative_count: int = 0
    average_star_rating: float = 0.0
    severity_score: float = 0.0
    candidate_quotes: List[str] = Field(default_factory=list)
    sample_reviews: List[SanitizedReview] = Field(default_factory=list)


class ClusteringResult(BaseModel):
    """Overall result of the thematic clustering pass."""
    total_reviews_analyzed: int
    reporting_period: str
    all_clusters: List[ThemeCluster] = Field(default_factory=list)
    top_3_clusters: List[ThemeCluster] = Field(default_factory=list)
    tokens_consumed: int = 0
    requests_consumed: int = 0
    tier2_disambiguated_count: int = 0


