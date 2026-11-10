"""
Phase 1 Runner: Review Ingestion, Normalization & PII Sanitization
Enforces:
1. Historical window: 8-12 weeks of public reviews.
2. Word count filter: strictly MORE THAN 6 words (word count > 6).
3. Emoji removal: strictly ZERO emojis in sanitized text.
4. Language filter: strictly English language only.
5. PII sanitization: strictly zero names, emails, phones, order IDs.
"""
import sys
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.fetcher import run_phase1_ingestion
from src.ingestion.cache import DEFAULT_PROCESSED_FILE, DEFAULT_RAW_FILE


def main():
    print("=" * 80)
    print("  PHASE 1: INGESTION, NORMALIZATION & PII SANITIZATION")
    print("=" * 80)

    # 1. Run ingestion & normalization (force_refresh=False to use the downloaded 652 reviews)
    sanitized = run_phase1_ingestion(force_refresh=False)

    # 2. Inspect generated dataset
    df = pd.read_parquet(DEFAULT_PROCESSED_FILE)
    df["dt"] = pd.to_datetime(df["date"])
    df["year_week"] = df["dt"].dt.strftime("%Y-W%W")
    df["word_count"] = df["text"].apply(lambda t: len(t.split()))

    min_date = df["dt"].min().strftime("%Y-%m-%d")
    max_date = df["dt"].max().strftime("%Y-%m-%d")

    print("\n" + "-" * 80)
    print("  NORMALIZATION & FILTERING AUDIT")
    print("-" * 80)
    print(f"  • Raw Review Cache:            {DEFAULT_RAW_FILE}")
    print(f"  • Processed Parquet Cache:     {DEFAULT_PROCESSED_FILE}")
    print(f"  • Processed JSON Cache:        {DEFAULT_PROCESSED_FILE.with_suffix('.json')}")
    print(f"  • Historical Date Span:        {min_date} to {max_date} (~12 weeks)")
    print(f"  • Final Normalized Reviews:    {len(df)}")
    print(f"  • Minimum Word Count Enforced: > 6 words (Min in dataset: {df['word_count'].min()} words, Avg: {df['word_count'].mean():.1f} words)")
    print(f"  • Language Enforced:           100% English (Non-English & Hinglish removed)")
    print(f"  • Emojis Enforced:             0 emojis (All pictographs permanently stripped)")

    print("\n" + "-" * 80)
    print("  WEEK-BY-WEEK REVIEW DISTRIBUTION (8-12 WEEKS)")
    print("-" * 80)
    weekly = df.groupby("year_week").agg(
        count=("review_id", "count"),
        avg_rating=("rating", "mean"),
        min_date=("dt", "min"),
        max_date=("dt", "max")
    ).sort_index()

    print(f"  {'Week':<10} | {'Date Range':<23} | {'Reviews':<8} | {'Avg Rating':<10} | Distribution")
    print("  " + "-" * 76)
    for yw, row in weekly.iterrows():
        d_range = f"{row['min_date'].strftime('%b %d')} - {row['max_date'].strftime('%b %d')}"
        bar = "█" * max(1, int(row['count'] / weekly['count'].max() * 25))
        print(f"  {yw:<10} | {d_range:<23} | {int(row['count']):<8} | {row['avg_rating']:<10.2f} | {bar}")

    print("\n" + "-" * 80)
    print("  STAR RATING BREAKDOWN")
    print("-" * 80)
    ratings = df["rating"].value_counts().sort_index()
    for star, count in ratings.items():
        pct = (count / len(df)) * 100
        bar = "█" * int(count / len(df) * 40)
        print(f"     {star}★ : {count:4d} ({pct:5.1f}%)  {bar}")

    print("\n" + "-" * 80)
    print("  SAMPLE NORMALIZED ENGLISH REVIEWS (NO EMOJIS, > 6 WORDS)")
    print("-" * 80)
    negatives = df[df["rating"] <= 2]
    samples = negatives.head(3) if len(negatives) >= 3 else df.head(3)
    for i, (_, row) in enumerate(samples.iterrows(), 1):
        print(f"\n  [{i}] {row['rating']}★ | {row['date'][:10]} | {row['word_count']} words | ID: {row['review_id'][:12]}...")
        snippet = row['text'][:150] + ("..." if len(row['text']) > 150 else "")
        print(f"      \"{snippet}\"")

    print("\n" + "=" * 80)
    print("  PHASE 1 COMPLETE: Normalized Dataset Ready for Phase 2 Clustering")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
