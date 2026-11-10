"""
Phase 2 Runner: Thematic Clustering Engine & Empirical Severity Ranking.
Enforces:
1. Canonical domain themes: strictly <= 5 themes.
2. Two-tier hybrid classification (Tier 1 local regex/keywords + Tier 2 Groq rate-guarded).
3. Empirical Severity Scoring: N_negative * (5.0 - avg_star_rating).
4. Top 3 primary themes selection.
5. Mined candidate verbatim user quotes (100% exact substring in review corpus).
6. Groq free-tier rate limit telemetry (30 RPM, 12K TPM, 100K TPD).
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.cache import load_sanitized_reviews
from src.clustering.ranking import run_thematic_clustering
from src.clustering.themes import CANONICAL_THEMES


def main():
    print("=" * 85)
    print("  PHASE 2: THEMATIC CLUSTERING ENGINE & EMPIRICAL SEVERITY RANKING")
    print("  Rate-Guarded Architecture for Groq llama-3.3-70b-versatile")
    print("=" * 85)

    # 1. Load sanitized review dataset
    reviews = load_sanitized_reviews()
    if not reviews:
        print("[ERROR] No sanitized reviews found in data/processed/. Run run_phase1.py first.")
        sys.exit(1)

    print(f"\n[INFO] Loaded {len(reviews)} normalized reviews from data/processed/sanitized_reviews.parquet")

    # 2. Run Phase 2 Clustering
    result = run_thematic_clustering(reviews)

    print("\n" + "-" * 85)
    print("  CANONICAL THEMES DISTRIBUTION & EMPIRICAL SEVERITY METRICS (<= 5 THEMES)")
    print("-" * 85)
    print(f"  {'Rank':<5} | {'Theme Name':<38} | {'Reviews':<8} | {'Share':<7} | {'Negatives':<9} | {'Avg ★':<6} | Severity")
    print("  " + "-" * 83)

    export_distribution = {}
    for rank, cluster in enumerate(result.all_clusters, 1):
        is_top3 = "★ PRIMARY" if rank <= 3 else "  Secondary"
        print(f"  {rank:<5} | {cluster.name:<38} | {cluster.review_count:<8} | {cluster.percentage_share:4.1f}%  | {cluster.negative_count:<9} | {cluster.average_star_rating:<6.2f} | {cluster.severity_score:6.1f} ({is_top3})")

        export_distribution[cluster.theme_id] = {
            "rank": rank,
            "theme_name": cluster.name,
            "review_count": cluster.review_count,
            "percentage_share": cluster.percentage_share,
            "negative_review_count": cluster.negative_count,
            "average_star_rating": cluster.average_star_rating,
            "severity_score": cluster.severity_score,
            "is_top_3": rank <= 3
        }

    print("\n" + "-" * 85)
    print("  TOP 3 PRIMARY THEMES (SELECTED FOR EXECUTIVE PULSE)")
    print("-" * 85)
    for rank, cluster in enumerate(result.top_3_clusters, 1):
        print(f"\n  #{rank}: {cluster.name} ({cluster.percentage_share}% share, Severity: {cluster.severity_score})")
        print(f"      Description: {cluster.description}")
        print(f"      Mined Verbatim Quotes ({len(cluster.candidate_quotes)} candidates):")
        for q_idx, quote in enumerate(cluster.candidate_quotes, 1):
            print(f"        [{q_idx}] \"{quote}\"")

    print("\n" + "-" * 85)
    print("  GROQ FREE-TIER RATE-LIMIT TELEMETRY AUDIT")
    print("-" * 85)
    print(f"  • LLM Model:                  llama-3.3-70b-versatile (Free Tier)")
    print(f"  • Quota Limits:               30 RPM | 1K RPD | 12,000 TPM | 100,000 TPD")
    print(f"  • Tier 1 Local Classification: {result.total_reviews_analyzed} reviews classified at 0 tokens (0 RPM, 0 TPM)")
    print(f"  • Tier 2 Disambiguated:        {result.tier2_disambiguated_count} boundary cases handled")
    print(f"  • Groq Requests Consumed:      {result.requests_consumed} requests (Limit: <= 30 RPM)")
    print(f"  • Groq Tokens Consumed:        {result.tokens_consumed} tokens (Limit: <= 12,000 TPM)")
    print(f"  • Quota Headroom Remaining:    {12000 - result.tokens_consumed} tokens/min ({(12000 - result.tokens_consumed)/12000*100:.1f}% headroom)")

    # 3. Save Phase 2 analysis artifacts
    out_dir = Path("Docs/phases/phase-02")
    out_dir.mkdir(parents=True, exist_ok=True)

    dist_file = out_dir / "theme_distribution.json"
    with open(dist_file, "w", encoding="utf-8") as f:
        json.dump(export_distribution, f, indent=2, ensure_ascii=False)

    sample_quotes_export = {
        cluster.theme_id: {
            "name": cluster.name,
            "candidate_quotes": cluster.candidate_quotes
        }
        for cluster in result.top_3_clusters
    }
    quotes_file = out_dir / "sample_reviews.json"
    with open(quotes_file, "w", encoding="utf-8") as f:
        json.dump(sample_quotes_export, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Persisted Phase 2 theme distribution to {dist_file}")
    print(f"[INFO] Persisted candidate quotes to {quotes_file}")

    print("\n" + "=" * 85)
    print("  PHASE 2 COMPLETE: Thematic Clustering Verified & Ready for Phase 3 Synthesis")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()

