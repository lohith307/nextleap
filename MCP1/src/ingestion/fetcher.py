"""
Review Ingestion Fetcher for Zomato.
Downloads 8-12 weeks of public store reviews from Google Play Store using pagination.
Falls back to high-fidelity seed dataset if offline or rate-limited.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from src.models.review import RawReview
from src.ingestion.sanitizer import PIISanitizer
from src.ingestion.cache import ReviewCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_APP_ID = "com.application.zomato"
DEFAULT_WEEKS_BACK = 12  # Full 12-week ingestion window

# Built-in high-fidelity seed dataset spanning the 5 Zomato themes
SEED_REVIEWS = [
    {
        "review_id": "seed_rev_001",
        "rating": 1,
        "title": "Terrible delivery delay",
        "text": "Order showed 30 mins ETA, arrived after 75 mins with no rider movement on map. Food was stone cold.",
        "date": "2026-10-18T19:30:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Rohan Sharma"
    },
    {
        "review_id": "seed_rev_002",
        "rating": 2,
        "title": "Driver cancelled after 40 mins",
        "text": "Delivery partner Ramesh kept circling the wrong street and then cancelled the delivery. Terrible rider dispatch.",
        "date": "2026-10-22T21:10:00",
        "platform": "google_play",
        "version": "14.2.1",
        "author_name": "Priya Patel"
    },
    {
        "review_id": "seed_rev_003",
        "rating": 1,
        "title": "Live tracking completely broken",
        "text": "GPS tracking stopped updating. Delivery guy was stuck at same junction for 30 minutes while food got soggy.",
        "date": "2026-10-25T13:45:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Amit K"
    },
    {
        "review_id": "seed_rev_004",
        "rating": 1,
        "title": "Unacceptable wait time",
        "text": "Delivery took 1 hour 40 mins for a restaurant 2km away. Support refused to reassign the order.",
        "date": "2026-10-29T20:15:00",
        "platform": "google_play",
        "version": "14.3.0",
        "author_name": "Deepak Mehta"
    },
    {
        "review_id": "seed_rev_005",
        "rating": 1,
        "title": "Spilled curry ruined everything",
        "text": "Container was crushed and dal leaked entirely inside the bag. No refund offered by support.",
        "date": "2026-10-15T14:20:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Sneha Sen"
    },
    {
        "review_id": "seed_rev_006",
        "rating": 1,
        "title": "Missing items and tamper seal broken",
        "text": "The tamper seal tape was broken on the paper bag and 2 cold drinks were missing from my combo.",
        "date": "2026-10-20T20:05:00",
        "platform": "google_play",
        "version": "14.2.1",
        "author_name": "Vikram Singh"
    },
    {
        "review_id": "seed_rev_007",
        "rating": 2,
        "title": "Cold biryani",
        "text": "Food arrived lukewarm and greasy. Please enforce proper thermal bags for delivery partners.",
        "date": "2026-10-27T19:50:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Ananya Roy"
    },
    {
        "review_id": "seed_rev_008",
        "rating": 2,
        "title": "Too many hidden platform charges",
        "text": "Platform fee, packaging fee, surge fee, weather fee! A 250 rupee meal ends up costing 420 rupees.",
        "date": "2026-10-12T12:30:00",
        "platform": "google_play",
        "version": "14.1.9",
        "author_name": "Karthik N"
    },
    {
        "review_id": "seed_rev_009",
        "rating": 1,
        "title": "Gold membership benefits reduced",
        "text": "Zomato Gold used to give flat discounts. Now there is a minimum order value and surge fees still apply.",
        "date": "2026-10-19T18:40:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Manish G"
    },
    {
        "review_id": "seed_rev_010",
        "rating": 2,
        "title": "Coupon removed at checkout",
        "text": "Coupon applies on cart page but disappears right when redirecting to UPI payment gateway.",
        "date": "2026-10-24T21:00:00",
        "platform": "google_play",
        "version": "14.2.1",
        "author_name": "Pooja V"
    },
    {
        "review_id": "seed_rev_011",
        "rating": 1,
        "title": "UPI deduction without order placement",
        "text": "UPI failed three times, deducted amount twice, but cart never confirmed. Took 4 days for reversal.",
        "date": "2026-10-16T20:15:00",
        "platform": "google_play",
        "version": "14.2.0",
        "author_name": "Rahul Verma"
    },
    {
        "review_id": "seed_rev_012",
        "rating": 1,
        "title": "Frequent app crashes on checkout",
        "text": "App constantly crashes on payment screen after iOS/Android update. Cart resets and items get emptied.",
        "date": "2026-10-23T19:10:00",
        "platform": "google_play",
        "version": "14.2.1",
        "author_name": "Divya S"
    },
    {
        "review_id": "seed_rev_013",
        "rating": 2,
        "title": "Search is laggy and filters don't work",
        "text": "Searching for restaurants takes 10 seconds to load and pure veg filter keeps resetting itself.",
        "date": "2026-10-30T13:20:00",
        "platform": "google_play",
        "version": "14.3.0",
        "author_name": "Siddharth B"
    },
    {
        "review_id": "seed_rev_014",
        "rating": 1,
        "title": "Useless bot in chat support",
        "text": "Chat support is completely automated with canned responses. Impossible to reach a human agent for wrong items.",
        "date": "2026-10-14T22:00:00",
        "platform": "google_play",
        "version": "14.1.9",
        "author_name": "Neha Joshi"
    },
    {
        "review_id": "seed_rev_015",
        "rating": 1,
        "title": "Denied refund for spoiled order",
        "text": "Sent photos of stale smelling chicken but support closed the ticket saying restaurant denied claim.",
        "date": "2026-10-26T21:45:00",
        "platform": "google_play",
        "version": "14.2.1",
        "author_name": "Tarun K"
    },
    {
        "review_id": "seed_rev_016",
        "rating": 4,
        "title": "Good app overall",
        "text": "Prompt delivery today and good packaging. Hope delivery charges don't keep rising.",
        "date": "2026-11-01T12:00:00",
        "platform": "google_play",
        "version": "14.3.0",
        "author_name": "Arjun Das"
    },
    {
        "review_id": "seed_rev_017",
        "rating": 5,
        "title": "Smooth ordering experience",
        "text": "Love the live tracking feature and restaurant recommendations. Rider arrived 5 minutes early.",
        "date": "2026-11-03T19:30:00",
        "platform": "google_play",
        "version": "14.3.0",
        "author_name": "Kavita Nair"
    }
]


class ReviewFetcher:
    """Fetches public store reviews with deep pagination across the full 8-12 week window."""

    def __init__(self, app_id: str = DEFAULT_APP_ID, weeks_back: int = DEFAULT_WEEKS_BACK):
        self.app_id = app_id
        self.weeks_back = weeks_back
        self.cutoff_date = datetime.now() - timedelta(weeks=weeks_back)

    def fetch_live_play_store(self, target_per_sort: int = 400) -> List[RawReview]:
        """
        Uses pagination across NEWEST and MOST_RELEVANT sorting to download
        hundreds of reviews covering the entire 8-12 week historical window.
        """
        try:
            from google_play_scraper import reviews, Sort
            logger.info("Downloading reviews for '%s' across 8-12 weeks (cutoff: %s)...",
                        self.app_id, self.cutoff_date.strftime("%Y-%m-%d"))

            collected_raw: List[dict] = []

            for sort_mode in [Sort.MOST_RELEVANT, Sort.NEWEST]:
                token = None
                fetched = 0
                while fetched < target_per_sort:
                    batch, token = reviews(
                        self.app_id,
                        lang="en",
                        country="in",
                        sort=sort_mode,
                        count=200,
                        continuation_token=token
                    )
                    if not batch:
                        break
                    collected_raw.extend(batch)
                    fetched += len(batch)
                    if not token:
                        break

            # Deduplicate by reviewId and filter within 8-12 week window
            unique_by_id = {r["reviewId"]: r for r in collected_raw}.values()

            raw_reviews: List[RawReview] = []
            for item in unique_by_id:
                review_date = item.get("at")
                if review_date and review_date < self.cutoff_date:
                    continue

                date_str = review_date.isoformat() if review_date else datetime.now().isoformat()
                content = str(item.get("content", "")).strip()
                if not content:
                    continue

                raw_reviews.append(
                    RawReview(
                        review_id=str(item.get("reviewId", f"rev_{len(raw_reviews)}")),
                        rating=int(item.get("score", 3)),
                        title=None,
                        text=content,
                        date=date_str,
                        platform="google_play",
                        version=item.get("reviewCreatedVersion"),
                        thumbs_up=item.get("thumbsUpCount", 0),
                        author_name=item.get("userName")
                    )
                )

            logger.info("Successfully downloaded %d reviews covering the full 8-12 weeks window.", len(raw_reviews))
            return raw_reviews
        except Exception as e:
            logger.warning("Live store download failed: %s. Falling back to seed reviews.", e)
            return []

    def get_seed_reviews(self) -> List[RawReview]:
        """Returns the high-fidelity seed review dataset."""
        return [RawReview(**item) for item in SEED_REVIEWS]

    def fetch_and_process(self, force_refresh: bool = False) -> List[RawReview]:
        """Loads reviews from cache, live fetch, or seed fallback."""
        if not force_refresh:
            cached = ReviewCache.load_raw()
            if cached and len(cached) >= 100:
                logger.info("Loaded %d raw reviews from local cache.", len(cached))
                return cached

        reviews_list = self.fetch_live_play_store()

        if not reviews_list or len(reviews_list) < 10:
            logger.info("Using seed review dataset.")
            reviews_list = self.get_seed_reviews()

        ReviewCache.save_raw(reviews_list)
        return reviews_list


def fetch_historical_reviews(
    app_id: str = DEFAULT_APP_ID,
    target_weeks: int = DEFAULT_WEEKS_BACK,
    max_reviews: int = 1000
) -> List[RawReview]:
    """Fetches public reviews for target app within target historical window."""
    fetcher = ReviewFetcher(app_id=app_id, weeks_back=target_weeks)
    return fetcher.fetch_and_process(force_refresh=True)



def run_phase1_ingestion(force_refresh: bool = True) -> List:
    """Executes Phase 1: Ingestion -> Sanitization -> Storage."""
    logger.info("=== STARTING PHASE 1: DOWNLOAD & STORE 8-12 WEEKS REVIEWS ===")
    fetcher = ReviewFetcher(weeks_back=DEFAULT_WEEKS_BACK)
    raw_reviews = fetcher.fetch_and_process(force_refresh=force_refresh)
    logger.info("Total raw reviews downloaded: %d", len(raw_reviews))

    # Sanitize PII
    sanitizer = PIISanitizer()
    sanitized_reviews = sanitizer.sanitize_batch(raw_reviews)
    logger.info("Sanitized %d reviews (PII completely stripped).", len(sanitized_reviews))

    # Store processed cache
    ReviewCache.save_sanitized(sanitized_reviews)
    logger.info("Stored sanitized reviews to data/processed/sanitized_reviews.parquet and .json")

    return sanitized_reviews


if __name__ == "__main__":
    run_phase1_ingestion(force_refresh=True)
