"""
Local cache management for raw and processed review datasets.
Supports Parquet and JSON serialization formats.
"""
import os
import json
from pathlib import Path
from typing import List, Optional
import pandas as pd
from src.models.review import RawReview, SanitizedReview

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_PROCESSED_FILE = DEFAULT_PROCESSED_DIR / "sanitized_reviews.parquet"
DEFAULT_PROCESSED_JSON = DEFAULT_PROCESSED_DIR / "sanitized_reviews.json"
DEFAULT_RAW_FILE = DEFAULT_RAW_DIR / "raw_reviews.json"


class ReviewCache:
    """Manages reading and writing reviews to local disk cache."""

    @staticmethod
    def ensure_directories():
        DEFAULT_RAW_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def save_raw(cls, reviews: List[RawReview], path: Path = DEFAULT_RAW_FILE) -> None:
        """Saves raw reviews to JSON cache."""
        cls.ensure_directories()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump() for r in reviews]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_raw(cls, path: Path = DEFAULT_RAW_FILE) -> Optional[List[RawReview]]:
        """Loads raw reviews from JSON cache if present."""
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [RawReview(**item) for item in data]

    @classmethod
    def save_sanitized(
        cls, reviews: List[SanitizedReview], path: Path = DEFAULT_PROCESSED_FILE
    ) -> None:
        """Saves sanitized reviews to Parquet (and JSON fallback)."""
        cls.ensure_directories()
        path.parent.mkdir(parents=True, exist_ok=True)

        dicts = [r.model_dump() for r in reviews]
        df = pd.DataFrame(dicts)

        # Write parquet
        try:
            df.to_parquet(str(path), index=False)
        except Exception:
            pass

        # Also write JSON for easy inspection and fallback
        json_path = path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dicts, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_sanitized(
        cls, path: Path = DEFAULT_PROCESSED_FILE
    ) -> Optional[List[SanitizedReview]]:
        """Loads sanitized reviews from Parquet or JSON fallback."""
        if path.exists():
            try:
                df = pd.read_parquet(str(path))
                return [SanitizedReview(**row) for row in df.to_dict(orient="records")]
            except Exception:
                pass

        json_path = path.with_suffix(".json")
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [SanitizedReview(**item) for item in data]

        return None


def load_sanitized_reviews(path: Path = DEFAULT_PROCESSED_FILE) -> Optional[List[SanitizedReview]]:
    """Convenience function to load sanitized reviews from cache."""
    return ReviewCache.load_sanitized(path)


def save_sanitized_reviews(reviews: List[SanitizedReview], path: Path = DEFAULT_PROCESSED_FILE) -> None:
    """Convenience function to save sanitized reviews to cache."""
    ReviewCache.save_sanitized(reviews, path)
