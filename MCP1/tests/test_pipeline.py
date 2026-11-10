"""
End-to-end Integration Tests for Phase 5 & Phase 6: Customer Voice Pulse Pipeline.
Verifies the complete orchestrated execution:
Ingestion -> Clustering -> Synthesis -> Veracity Guardrails -> MCP Publishing.
"""
import pytest
from pathlib import Path
from src.pipeline import CustomerVoicePulsePipeline, PipelineResult
from src.synthesis.verifier import is_substring_in_corpus
from src.synthesis.budget import count_words


def test_pipeline_dry_run():
    """Assert pipeline executes cleanly in dry-run mode without publishing."""
    pipeline = CustomerVoicePulsePipeline()
    result: PipelineResult = pipeline.run(dry_run=True)

    assert result.status == "SUCCESS"
    assert result.total_reviews_analyzed > 0
    assert result.dry_run is True
    assert result.document_url is None
    assert result.draft_id is None

    # Verify report constraints
    report = result.pulse_report
    assert len(report.top_themes) == 3
    assert len(report.verbatim_quotes) == 3
    assert len(report.action_ideas) == 3
    assert report.word_count <= 250
    assert report.quote_veracity_verified is True
    assert report.pii_free_verified is True


def test_pipeline_live_mcp_run():
    """Assert pipeline executes end-to-end and successfully publishes via MCP."""
    pipeline = CustomerVoicePulsePipeline(
        recipient_email="test-stakeholder@zomato.internal"
    )
    result: PipelineResult = pipeline.run(dry_run=False)

    assert result.status == "SUCCESS"
    assert result.dry_run is False

    # Check Google Docs MCP output
    assert result.document_url is not None
    assert "https://docs.google.com/document/d/" in result.document_url
    assert result.document_id is not None

    # Check Gmail MCP output
    assert result.draft_id is not None
    assert len(result.draft_id) > 0

    # Check local persistent backup
    backup_path = Path(result.local_pulse_path)
    assert backup_path.exists()
    content = backup_path.read_text(encoding="utf-8")
    assert count_words(content) <= 250


def test_pipeline_custom_doc_id():
    """Assert pipeline accepts custom doc_id and forwards it to MCP."""
    custom_doc = "1customDocIdTesting123"
    pipeline = CustomerVoicePulsePipeline(
        recipient_email="test-custom-doc@zomato.internal"
    )
    result = pipeline.run(dry_run=False, doc_id=custom_doc)
    assert result.document_id == custom_doc
    assert custom_doc in result.document_url


def test_main_cli_dry_run(monkeypatch, capsys):
    """Assert main.py CLI executes cleanly in --dry-run mode."""
    from main import main as cli_main
    monkeypatch.setattr("sys.argv", ["main.py", "--dry-run"])
    cli_main()
    captured = capsys.readouterr()
    assert "ZOMATO CUSTOMER VOICE PULSE & MCP DELIVERY PLATFORM" in captured.out
    assert "SUCCESS" in captured.out
    assert "MCP Publishing:           SKIPPED (--dry-run enabled)" in captured.out

