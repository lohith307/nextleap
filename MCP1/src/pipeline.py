"""
End-to-End Master Orchestrator Pipeline for Zomato Customer Review Pulse.
Integrates:
1. Ingestion & PII Sanitization (Phase 1)
2. Two-Tier Thematic Clustering & Severity Ranking (Phase 2)
3. Groq LLM Pulse Synthesis & Verbatim Verification (Phase 3)
4. Model Context Protocol (MCP) Google Docs & Gmail Publishing (Phase 4)
"""
import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field

from src.models.review import SanitizedReview
from src.models.theme import ClusteringResult
from src.models.pulse import WeeklyPulseReport
from src.ingestion.cache import ReviewCache, load_sanitized_reviews, save_sanitized_reviews
from src.ingestion.fetcher import fetch_historical_reviews
from src.ingestion.sanitizer import PIISanitizer
from src.clustering.ranking import run_thematic_clustering
from src.synthesis.prompter import synthesize_pulse
from src.mcp_client.docs_adapter import GoogleDocsAdapter
from src.mcp_client.gmail_adapter import GmailAdapter

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Execution result of the full end-to-end pipeline run."""
    status: str
    date_range: str
    total_reviews_analyzed: int
    pulse_report: WeeklyPulseReport
    document_url: Optional[str] = None
    document_id: Optional[str] = None
    draft_id: Optional[str] = None
    local_pulse_path: str = "Docs/generated_pulse.md"
    dry_run: bool = False
    tokens_consumed: int = 0
    model_used: str = "llama-3.3-70b-versatile"


class CustomerVoicePulsePipeline:
    """
    Master pipeline orchestrating data ingestion, clustering, synthesis, and MCP delivery.
    """

    def __init__(
        self,
        app_id: str = "com.application.zomato",
        recipient_email: Optional[str] = None,
        llm_model: Optional[str] = None,
        docs_adapter: Optional[GoogleDocsAdapter] = None,
        gmail_adapter: Optional[GmailAdapter] = None
    ):
        self.app_id = app_id
        self.recipient_email = (
            recipient_email
            or os.getenv("STAKEHOLDER_RECIPIENT_EMAIL")
            or os.getenv("RECIPIENT_EMAIL")
            or "product-team@zomato.internal"
        ).strip()
        self.llm_model = llm_model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.docs_adapter = docs_adapter or GoogleDocsAdapter()
        self.gmail_adapter = gmail_adapter or GmailAdapter()

    def run(
        self,
        refresh_cache: bool = False,
        dry_run: bool = False,
        max_reviews: int = 1000,
        doc_id: Optional[str] = None
    ) -> PipelineResult:
        """
        Executes the full pipeline workflow.
        """
        logger.info("=== Starting Zomato Customer Review Pulse Pipeline ===")

        # Step 1: Ingestion & Cache Check
        reviews: Optional[List[SanitizedReview]] = None
        if not refresh_cache:
            reviews = load_sanitized_reviews()

        if not reviews:
            logger.info("No cached processed reviews found or refresh requested. Fetching fresh reviews...")
            raw_reviews = fetch_historical_reviews(
                app_id=self.app_id,
                target_weeks=12,
                max_reviews=max_reviews
            )
            ReviewCache.save_raw(raw_reviews)
            sanitizer = PIISanitizer()
            reviews = sanitizer.sanitize_batch(raw_reviews)
            save_sanitized_reviews(reviews)
            logger.info(f"Ingested and sanitized {len(reviews)} reviews.")
        else:
            logger.info(f"Loaded {len(reviews)} sanitized reviews from local cache.")

        # Step 2: Thematic Clustering & Severity Ranking
        logger.info("Clustering reviews into <= 5 canonical themes and computing severity scores...")
        clustering_result: ClusteringResult = run_thematic_clustering(reviews)
        logger.info(f"Top 3 themes identified: {[c.name for c in clustering_result.top_3_clusters]}")

        # Step 3: Executive Pulse Synthesis via Groq LLM
        logger.info(f"Synthesizing Weekly Pulse report using {self.llm_model}...")
        pulse_report: WeeklyPulseReport = synthesize_pulse(
            clustering_result=clustering_result,
            all_reviews=reviews,
            model_name=self.llm_model
        )
        logger.info(
            f"Pulse synthesized. Word count: {pulse_report.word_count} words. "
            f"Veracity verified: {pulse_report.quote_veracity_verified}. "
            f"PII clean: {pulse_report.pii_free_verified}."
        )

        # Step 4: Always save local markdown backup
        backup_path = Path("Docs/generated_pulse.md")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(pulse_report.weekly_pulse_markdown)

        doc_url = None
        target_doc_id = doc_id or os.getenv("GOOGLE_DOC_ID")
        res_doc_id = None
        draft_id = None

        # Step 5: Model Context Protocol (MCP) Publishing
        if not dry_run:
            logger.info("Publishing via Model Context Protocol (MCP)...")

            # 5a: Google Docs via MCP tool call
            doc_title = f"Zomato Customer Voice Pulse — {pulse_report.date_range}"
            docs_res = self.docs_adapter.create_document(
                title=doc_title,
                content=pulse_report.weekly_pulse_markdown,
                doc_id=target_doc_id
            )
            doc_url = docs_res.get("document_url")
            res_doc_id = docs_res.get("document_id") or target_doc_id
            logger.info(f"Google Doc created via MCP: {doc_url}")

            # 5b: Gmail Draft via MCP tool call
            email_subject = f"Weekly Customer Voice Pulse: Zomato ({pulse_report.date_range})"
            email_body = (
                f"Hi Team,\n\n"
                f"The weekly executive Customer Voice Pulse for Zomato ({pulse_report.date_range}) "
                f"has been generated and published.\n\n"
                f"Google Doc Link:\n{doc_url}\n\n"
                f"---\n"
                f"EXECUTIVE SUMMARY:\n\n"
                f"{pulse_report.weekly_pulse_markdown}\n\n"
                f"---\n"
                f"Generated automatically by Zomato Customer Review Pulse Platform via MCP."
            )
            gmail_res = self.gmail_adapter.create_draft(
                recipient=self.recipient_email,
                subject=email_subject,
                body=email_body
            )
            draft_id = gmail_res.get("draft_id")
            logger.info(f"Gmail draft created via MCP: {draft_id} for recipient {self.recipient_email}")

        else:
            logger.info("Dry-run mode enabled. Skipped MCP publishing.")

        return PipelineResult(
            status="SUCCESS",
            date_range=pulse_report.date_range,
            total_reviews_analyzed=len(reviews),
            pulse_report=pulse_report,
            document_url=doc_url,
            document_id=res_doc_id,
            draft_id=draft_id,
            local_pulse_path=str(backup_path),
            dry_run=dry_run,
            tokens_consumed=pulse_report.tokens_consumed,
            model_used=pulse_report.model_used
        )

