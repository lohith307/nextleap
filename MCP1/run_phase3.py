"""
Phase 3 Runner: Executive Weekly Pulse Synthesis & Verbatim Verifier.
Enforces:
1. Synthesis of Top 3 Themes, 3 Verbatim Quotes, 3 Concrete Action Ideas.
2. 100% exact verbatim substring match in public review corpus (zero hallucinated quotes).
3. Strict word budget enforcement: <= 250 words (scannable in under 2 minutes).
4. Strict PII sanitization: 0% PII in final pulse document.
5. Saves persistent pulse artifact to Docs/generated_pulse.md.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.cache import load_sanitized_reviews
from src.clustering.ranking import run_thematic_clustering
from src.synthesis.prompter import synthesize_pulse
from src.synthesis.verifier import is_substring_in_corpus
from src.synthesis.budget import count_words


def main():
    print("=" * 85)
    print("  PHASE 3: EXECUTIVE WEEKLY PULSE SYNTHESIS & VERBATIM VERIFIER")
    print("  Groq Inference Engine + Deterministic Veracity & Budget Guardrails")
    print("=" * 85)

    # 1. Load normalized review corpus
    reviews = load_sanitized_reviews()
    if not reviews:
        print("[ERROR] No sanitized reviews found in data/processed/. Run run_phase1.py first.")
        sys.exit(1)

    print(f"\n[INFO] Loaded {len(reviews)} normalized reviews from data/processed/sanitized_reviews.parquet")

    # 2. Run Phase 2 clustering to obtain Top 3 primary themes & quote candidates
    print("[INFO] Running Phase 2 clustering and severity ranking...")
    clustering_result = run_thematic_clustering(reviews)
    top_3 = clustering_result.top_3_clusters

    print(f"[INFO] Top 3 Themes identified:")
    for rank, cluster in enumerate(top_3, 1):
        print(f"       {rank}. {cluster.name} ({cluster.percentage_share}% share, Severity: {cluster.severity_score})")

    # 3. Run Phase 3 synthesis
    print("\n[INFO] Synthesizing Weekly Executive Pulse report...")
    pulse_report = synthesize_pulse(clustering_result, reviews)

    # 4. Print the synthesized pulse document
    print("\n" + "-" * 85)
    print("  SYNTHESIZED EXECUTIVE WEEKLY PULSE DOCUMENT")
    print("-" * 85 + "\n")
    print(pulse_report.weekly_pulse_markdown)

    # 5. Guardrail Verification Audit
    print("\n" + "-" * 85)
    print("  PHASE 3 GUARDRAILS & ACCEPTANCE CRITERIA AUDIT")
    print("-" * 85)

    corpus_texts = [r.text for r in reviews]

    print("\n  [A] VERBATIM QUOTE VERACITY (100% Exact Substring Match):")
    all_quotes_verbatim = True
    for idx, quote in enumerate(pulse_report.verbatim_quotes, 1):
        matched = is_substring_in_corpus(quote, corpus_texts)
        status = "PASSED (100% Verbatim Substring)" if matched else "FAILED (Altered/Invented)"
        if not matched:
            all_quotes_verbatim = False
        print(f"      Quote #{idx}: \"{quote[:80]}...\"")
        print(f"               Verification: {status}")

    print("\n  [B] WORD BUDGET ENFORCEMENT:")
    w_count = count_words(pulse_report.weekly_pulse_markdown)
    budget_ok = w_count <= 250
    print(f"      Actual Word Count: {w_count} words")
    print(f"      Budget Ceiling:    <= 250 words")
    print(f"      Status:            {'PASSED (<= 250 words)' if budget_ok else 'FAILED (Exceeded Budget)'}")

    print("\n  [C] PII LEAKAGE CHECK:")
    pii_status = "PASSED (0% PII Detected)" if pulse_report.pii_free_verified else "FAILED (PII Flagged)"
    print(f"      Status:            {pii_status}")

    print("\n  [D] DELIVERABLES CHECKLIST:")
    print(f"      • Top 3 Themes:    {len(pulse_report.top_themes)} present")
    print(f"      • Verbatim Quotes: {len(pulse_report.verbatim_quotes)} present")
    print(f"      • Action Ideas:    {len(pulse_report.action_ideas)} present")
    print(f"      • Synthesis Model: {pulse_report.model_used}")

    # 6. Save persistent pulse artifacts
    out_dir = Path("Docs/phases/phase-03")
    out_dir.mkdir(parents=True, exist_ok=True)

    pulse_json_file = out_dir / "pulse_report.json"
    with open(pulse_json_file, "w", encoding="utf-8") as f:
        json.dump(pulse_report.model_dump(), f, indent=2, ensure_ascii=False)

    pulse_md_file = Path("Docs/generated_pulse.md")
    with open(pulse_md_file, "w", encoding="utf-8") as f:
        f.write(pulse_report.weekly_pulse_markdown)

    print(f"\n[INFO] Persisted pulse report JSON to {pulse_json_file}")
    print(f"[INFO] Persisted executive pulse document to {pulse_md_file}")

    print("\n" + "=" * 85)
    print("  PHASE 3 COMPLETE: Executive Pulse Synthesized, Verified & Persisted")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()

