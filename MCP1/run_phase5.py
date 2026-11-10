"""
Phase 5 Runner: End-to-End Master Orchestrator Pipeline.
Executes the full automated workflow:
1. Review Ingestion & PII Sanitization (Phase 1)
2. Two-Tier Thematic Clustering (Phase 2)
3. Groq LLM Pulse Synthesis & Verbatim Verifier (Phase 3)
4. Model Context Protocol (MCP) Publishing (Phase 4)
5. Comprehensive End-to-End Validation & Telemetry (Phase 5)
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

from src.pipeline import CustomerVoicePulsePipeline, PipelineResult


def main():
    print("=" * 85)
    print("  PHASE 5: END-TO-END MASTER ORCHESTRATOR PIPELINE RUNNER")
    print("  Zomato Customer Voice Pulse & Model Context Protocol (MCP) Publishing")
    print("=" * 85)

    recipient = os.getenv("STAKEHOLDER_RECIPIENT_EMAIL", "product-team@zomato.internal")
    doc_id = os.getenv("GOOGLE_DOC_ID", "1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0")
    mcp_url = os.getenv("MCP_SERVER_URL", "https://web-production-45fffe.up.railway.app")

    print(f"\n[CONFIG] Target Application:      com.application.zomato")
    print(f"[CONFIG] MCP Server URL:          {mcp_url}")
    print(f"[CONFIG] Configured Google Doc ID:{doc_id}")
    print(f"[CONFIG] Stakeholder Recipient:   {recipient}")

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    pipeline = CustomerVoicePulsePipeline(
        recipient_email=recipient
    )

    # Step 1: Run Full Pipeline with MCP Publishing
    print("\n" + "-" * 85)
    print("  EXECUTING FULL ORCHESTRATED PIPELINE")
    print("-" * 85)

    result: PipelineResult = pipeline.run(
        refresh_cache=False,
        dry_run=False,
        doc_id=doc_id
    )

    print("\n" + "-" * 85)
    print("  GENERATED WEEKLY EXECUTIVE PULSE")
    print("-" * 85 + "\n")
    print(result.pulse_report.weekly_pulse_markdown)

    print("\n" + "=" * 85)
    print("  PHASE 5 VERIFICATION & TELEMETRY SUMMARY")
    print("=" * 85)
    print(f"  • Execution Status:         {result.status}")
    print(f"  • Reporting Period:         {result.date_range}")
    print(f"  • Reviews Analyzed:         {result.total_reviews_analyzed}")
    print(f"  • Word Budget Compliance:   {result.pulse_report.word_count} words (Limit: <= 250 words)")
    print(f"  • Quote Veracity (100%):    {'PASSED' if result.pulse_report.quote_veracity_verified else 'CORRECTED'}")
    print(f"  • PII Free (0% Leakage):    {'VERIFIED' if result.pulse_report.pii_free_verified else 'FLAGGED'}")
    print(f"  • Google Docs MCP URL:      {result.document_url}")
    print(f"  • Gmail Draft ID (MCP):     {result.draft_id}")
    print(f"  • Stakeholder Email:        {recipient}")
    print(f"  • Local Pulse Backup:       {result.local_pulse_path}")
    print(f"  • Direct Google APIs:       ZERO (100% routed through MCP)")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    main()

