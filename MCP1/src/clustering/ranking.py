"""
Empirical ranking and Top 3 theme selector for Zomato Customer Reviews.
Calculates Severity Scores and mines candidate verbatim quotes.
"""
from typing import List, Optional
from datetime import datetime
from src.models.review import SanitizedReview
from src.models.theme import ThemeCluster, ClusteringResult
from src.clustering.themes import CANONICAL_THEMES
from src.clustering.classifier import ThematicClassifier


def calculate_theme_metrics(
    theme_id: str,
    reviews_in_theme: List[SanitizedReview],
    total_reviews: int,
    classifier: ThematicClassifier
) -> ThemeCluster:
    """
    Computes statistical and severity metrics for a single theme cluster.
    Severity Formula: N_negative * (5.0 - avg_star_rating)
    """
    t_def = CANONICAL_THEMES[theme_id]
    review_count = len(reviews_in_theme)

    if total_reviews == 0 or review_count == 0:
        return ThemeCluster(
            theme_id=theme_id,
            name=t_def.name,
            description=t_def.description,
            review_count=0,
            percentage_share=0.0,
            negative_count=0,
            average_star_rating=0.0,
            severity_score=0.0,
            candidate_quotes=[],
            sample_reviews=[]
        )

    percentage_share = round((review_count / total_reviews) * 100.0, 1)
    negative_reviews = [r for r in reviews_in_theme if r.rating <= 2]
    negative_count = len(negative_reviews)
    avg_rating = round(sum(r.rating for r in reviews_in_theme) / review_count, 2)
    severity_score = round(negative_count * (5.0 - avg_rating), 1)

    candidate_quotes = classifier.extract_candidate_quotes(
        reviews_in_theme,
        max_quotes=4,
        theme_id=theme_id
    )

    return ThemeCluster(
        theme_id=theme_id,
        name=t_def.name,
        description=t_def.description,
        review_count=review_count,
        percentage_share=percentage_share,
        negative_count=negative_count,
        average_star_rating=avg_rating,
        severity_score=severity_score,
        candidate_quotes=candidate_quotes,
        sample_reviews=reviews_in_theme[:5]
    )


def run_thematic_clustering(
    reviews: List[SanitizedReview],
    reporting_period: Optional[str] = None,
    classifier: Optional[ThematicClassifier] = None
) -> ClusteringResult:
    """
    Executes the full Phase 2 thematic clustering pipeline.
    
    1. Clusters all reviews locally across canonical themes (0 tokens, 0 RPM).
    2. Runs Tier 2 boundary disambiguation for tied/ambiguous reviews (Groq rate-guarded).
    3. Calculates volume, negative count, star ratings, and severity scores.
    4. Ranks clusters by empirical Severity Score descending.
    5. Selects the Top 3 themes.
    6. Mines 3-4 candidate verbatim quotes per theme.
    7. Tracks Groq token and request telemetry (strictly <= 1,500 tokens, <= 2 calls).
    """
    clf = classifier or ThematicClassifier()
    clustered_dict, disambiguated_count = clf.cluster_reviews(reviews)
    total_reviews = len(reviews)

    # Calculate date range if not provided
    if not reporting_period and reviews:
        dates = [r.date for r in reviews if r.date]
        if dates:
            dates.sort()
            d_start = str(dates[0]).split("T")[0]
            d_end = str(dates[-1]).split("T")[0]
            reporting_period = f"{d_start} to {d_end}"
        else:
            reporting_period = "Last 8-12 weeks"
    elif not reporting_period:
        reporting_period = "Recent"

    all_clusters: List[ThemeCluster] = []
    for theme_id in CANONICAL_THEMES:
        cluster = calculate_theme_metrics(
            theme_id=theme_id,
            reviews_in_theme=clustered_dict.get(theme_id, []),
            total_reviews=total_reviews,
            classifier=clf
        )
        all_clusters.append(cluster)

    # Rank clusters by empirical Severity Score descending
    all_clusters.sort(key=lambda c: c.severity_score, reverse=True)

    # Exactly top 3 themes
    top_3 = all_clusters[:3]

    return ClusteringResult(
        total_reviews_analyzed=total_reviews,
        reporting_period=reporting_period,
        all_clusters=all_clusters,
        top_3_clusters=top_3,
        tokens_consumed=clf.rate_limiter.tokens_consumed,
        requests_consumed=clf.rate_limiter.requests_consumed,
        tier2_disambiguated_count=disambiguated_count
    )
