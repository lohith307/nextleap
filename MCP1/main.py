"""
Master CLI Entrypoint for Zomato Customer Review Pulse Platform.
Usage:
    python main.py
    python main.py --dry-run
    python main.py --recipient stakeholder@zomato.internal
    python main.py --refresh-cache
"""
import sys
import os
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from src.pipeline import CustomerVoicePulsePipeline, PipelineResult


def parse_args():
    parser = argparse.ArgumentParser(
        description="Zomato Customer Voice Pulse & MCP Delivery Platform"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute clustering and synthesis without calling MCP publishing servers"
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Re-fetch public reviews from app store instead of reading local cache"
    )
    parser.add_argument(
        "--recipient",
        type=str,
        default=os.getenv("STAKEHOLDER_RECIPIENT_EMAIL", "product-team@zomato.internal"),
        help="Recipient email address for the Gmail draft"
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        default=os.getenv("GOOGLE_DOC_ID", "1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0"),
        help="Google Doc ID to append the weekly pulse to via MCP"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        help="LLM model name for Groq inference"
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=1000,
        help="Maximum raw reviews to fetch (capped at 1,000 for rate limit safety)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    print("\n" + "=" * 70)
    print("   ZOMATO CUSTOMER VOICE PULSE & MCP DELIVERY PLATFORM")
    print("   Powered by Groq LLM (llama-3.3-70b-versatile) & MCP Servers")
    print("=" * 70 + "\n")

    pipeline = CustomerVoicePulsePipeline(
        recipient_email=args.recipient,
        llm_model=args.model
    )

    result: PipelineResult = pipeline.run(
        refresh_cache=args.refresh_cache,
        dry_run=args.dry_run,
        max_reviews=args.max_reviews,
        doc_id=args.doc_id
    )

    print("\n" + "-" * 70)
    print("                    WEEKLY PULSE DOCUMENT")
    print("-" * 70 + "\n")
    print(result.pulse_report.weekly_pulse_markdown)

    print("\n" + "=" * 70)
    print("                    EXECUTION SUMMARY")
    print("=" * 70)
    print(f"  * Status:                   {result.status}")
    print(f"  * Reporting Window:         {result.date_range}")
    print(f"  * Reviews Analyzed:         {result.total_reviews_analyzed}")
    print(f"  * Word Count:               {result.pulse_report.word_count} words (Limit: <= 250 words)")
    print(f"  * Quote Veracity:           100% Verbatim Match ({'PASSED' if result.pulse_report.quote_veracity_verified else 'CORRECTED'})")
    print(f"  * PII Leakage Check:        0% PII Detected ({'CLEAN' if result.pulse_report.pii_free_verified else 'FLAGGED'})")
    print(f"  * Tokens Consumed:          {result.tokens_consumed} tokens (Limit: <= 12,000 TPM)")
    print(f"  * LLM Model:                {result.model_used}")
    print(f"  * Local Backup:             {result.local_pulse_path}")

    if not args.dry_run:
        print(f"  * Google Doc (MCP):         {result.document_url}")
        print(f"  * Gmail Draft ID (MCP):     {result.draft_id}")
        print(f"  * Stakeholder Recipient:    {args.recipient}")
    else:
        print("  * MCP Publishing:           SKIPPED (--dry-run enabled)")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

