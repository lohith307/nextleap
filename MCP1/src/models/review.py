"""
Domain models for Zomato Customer Review Pulse pipeline.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class RawReview(BaseModel):
    """Raw review fetched from public app store exports."""
    review_id: str
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = None
    text: str
    date: Optional[str] = None  # ISO format string or YYYY-MM-DD
    platform: str = "google_play"  # google_play or app_store
    version: Optional[str] = None
    thumbs_up: Optional[int] = 0
    author_name: Optional[str] = None  # Will be scrubbed in sanitization


class SanitizedReview(BaseModel):
    """
    Sanitized review guaranteed free of PII (names, handles, emails, phone numbers, order IDs).
    """
    review_id: str
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = None
    text: str
    date: Optional[str] = None
    platform: str = "google_play"
    version: Optional[str] = None
    thumbs_up: Optional[int] = 0
    cluster_id: Optional[str] = None  # To be assigned in Phase 2

