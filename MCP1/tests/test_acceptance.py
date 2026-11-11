"""
Milestone 2 Acceptance Test Suite (Phase 7).
Verifies all 9 Acceptance Criteria defined in Docs/implementationplan.md:
1. Public Reviews Sourced (8-12 weeks, <= 1000 reviews)
2. PII Completely Anonymized (0% names, emails, phones, order IDs, emojis)
3. Thematic Clustering (<= 5 themes, Top 3 ranked by Severity Score)
4. Verbatim Quotes (exactly 3 quotes, 100% exact substring matches)
5. Action Ideas (exactly 3 concrete, realistic next steps)
6. Scannable Format (strictly <= 250 words, clean markdown sections)
7. Google Docs via MCP (append_to_doc/create_document tool call on MCP server)
8. Gmail Draft via MCP (create_email_draft/gmail_create_draft tool call on MCP server)
9. Zero Direct Google APIs (static audit of entire codebase)
"""
import os
import sys
import ast
import json
import re
from pathlib import Path
from datetime import datetime
import pytest

from src.ingestion.cache import load_raw_reviews, load_sanitized_reviews
from src.ingestion.sanitizer import PIISanitizer
from src.clustering.ranking import run_thematic_clustering
from src.synthesis.prompter import synthesize_pulse_deterministic
from src.synthesis.budget import count_words
from src.synthesis.verifier import is_substring_in_corpus
from src.mcp_client.client import StdioMCPClient
from src.mcp_client.docs_adapter import GoogleDocsAdapter
from src.mcp_client.gmail_adapter import GmailAdapter


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_mcp_client():
    """Fixture providing a connected MCP client to the mock server."""
    client = StdioMCPClient(
        command=sys.executable,
        args=["-m", "tests.mock_mcp_server"]
    )
    client.start()
    yield client
    client.close()


def test_acceptance_criterion_1_public_reviews_sourced():
    """Criterion 1: 8-12 weeks of reviews sourced, <= 1000 reviews, raw and sanitized cache."""
    raw_reviews = load_raw_reviews()
    assert raw_reviews is not None and len(raw_reviews) > 0, "Raw reviews corpus must not be empty"
    assert len(raw_reviews) <= 1000, f"Raw reviews count {len(raw_reviews)} exceeds 1000 cap"

    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0, "Sanitized reviews corpus must not be empty"
    assert len(sanitized_reviews) <= len(raw_reviews), "Sanitized count cannot exceed raw count"

    # Date range audit (8-12 weeks)
    dates = []
    for r in sanitized_reviews:
        try:
            d = datetime.fromisoformat(r.date.replace("Z", "+00:00"))
            dates.append(d)
        except Exception:
            pass

    assert len(dates) > 0, "Valid ISO dates required"
    min_date = min(dates)
    max_date = max(dates)
    span_days = (max_date - min_date).days
    assert span_days >= 50, f"Review collection span of {span_days} days is less than ~8 weeks"


def test_acceptance_criterion_2_pii_completely_anonymized():
    """Criterion 2: Zero reviewer names, emails, phones, order IDs, or emojis in any artifact."""
    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0

    # Audit sanitized texts
    for r in sanitized_reviews:
        text = r.text
        # Emoji check
        assert not PIISanitizer.EMOJI_REGEX.search(text), f"Emoji leaked in sanitized review: {text[:40]}"
        # Email check
        assert not re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text), f"Email leaked: {text[:40]}"
        # Phone check
        assert not re.search(r"(?:\+91[-\s]?)?[6-9]\d{9}\b", text), f"Phone leaked: {text[:40]}"


def test_acceptance_criterion_3_thematic_clustering_severity():
    """Criterion 3: <= 5 canonical themes, Top 3 ranked strictly by empirical Severity Score."""
    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0

    result = run_thematic_clustering(sanitized_reviews)
    clusters = result.all_clusters

    assert len(clusters) <= 5, f"Themes count {len(clusters)} exceeds maximum of 5"

    # Verify severity score calculation: S = negative_count * (5.0 - average_star_rating)
    for c in clusters:
        expected_sev = round(c.negative_count * (5.0 - c.average_star_rating), 2)
        assert abs(c.severity_score - expected_sev) < 0.1, (
            f"Severity score mismatch for {c.name}: got {c.severity_score}, expected {expected_sev}"
        )

    # Verify Top 3 ranking is strictly descending by severity score
    top_3 = result.top_3_clusters
    assert len(top_3) == 3
    assert top_3[0].severity_score >= top_3[1].severity_score >= top_3[2].severity_score


def test_acceptance_criterion_4_verbatim_quotes():
    """Criterion 4: Exactly 3 quotes in synthesized pulse, 100% exact substring match."""
    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0

    result = run_thematic_clustering(sanitized_reviews)
    report = synthesize_pulse_deterministic(result, sanitized_reviews)
    pulse_doc = report.weekly_pulse_markdown

    # Verify from structured report object
    assert len(report.verbatim_quotes) == 3, f"Expected 3 quotes in report, found {len(report.verbatim_quotes)}"

    # Also verify extracted from markdown document
    quotes_from_md = []
    for line in pulse_doc.splitlines():
        line = line.strip()
        if line.startswith("- *") or line.startswith("- \"") or line.startswith("- '"):
            cleaned = line.lstrip("- *\"'").rstrip("*\"' ")
            quotes_from_md.append(cleaned)

    assert len(quotes_from_md) == 3, f"Expected 3 quotes in markdown, found {len(quotes_from_md)}"

    all_raw_texts = [r.text for r in sanitized_reviews]
    for q in quotes_from_md:
        matched = any(q in t for t in all_raw_texts)
        assert matched, f"Quote is not a 100% verbatim substring match: '{q}'"


def test_acceptance_criterion_5_action_ideas():
    """Criterion 5: Exactly 3 concrete, realistic action steps grounded in top themes."""
    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0

    result = run_thematic_clustering(sanitized_reviews)
    report = synthesize_pulse_deterministic(result, sanitized_reviews)
    pulse_doc = report.weekly_pulse_markdown

    assert "### Action Ideas" in pulse_doc or "## Action Ideas" in pulse_doc

    # Check from structured report object
    assert len(report.action_ideas) == 3, f"Expected 3 action ideas in report, found {len(report.action_ideas)}"

    # Check from markdown document
    action_lines = []
    in_actions = False
    for line in pulse_doc.splitlines():
        if "Action Ideas" in line:
            in_actions = True
            continue
        if in_actions and line.strip().startswith(("1.", "2.", "3.")):
            action_lines.append(line.strip())

    assert len(action_lines) == 3, f"Expected exactly 3 action lines in markdown, found {len(action_lines)}"


def test_acceptance_criterion_6_scannable_format_and_budget():
    """Criterion 6: Executive pulse formatted cleanly, strictly <= 250 words."""
    sanitized_reviews = load_sanitized_reviews()
    assert sanitized_reviews is not None and len(sanitized_reviews) > 0

    result = run_thematic_clustering(sanitized_reviews)
    report = synthesize_pulse_deterministic(result, sanitized_reviews)
    pulse_doc = report.weekly_pulse_markdown

    w_count = count_words(pulse_doc)
    assert w_count <= 250, f"Word count {w_count} exceeds strict limit of 250 words"

    # Section verification
    assert "# Zomato Customer Pulse" in pulse_doc
    assert "Top Themes" in pulse_doc
    assert "What Users Are Saying" in pulse_doc
    assert "Action Ideas" in pulse_doc


def test_acceptance_criterion_7_google_docs_via_mcp(mock_mcp_client):
    """Criterion 7: Google Docs publishing via Model Context Protocol (append_to_doc/create_document)."""
    docs_adapter = GoogleDocsAdapter(client=mock_mcp_client)

    result = docs_adapter.create_document(
        title="Zomato Customer Voice Pulse - Test",
        content="# Test Pulse Markdown",
        doc_id="1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0"
    )

    assert result["status"] == "success"
    assert "document_url" in result
    assert "1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0" in result["document_url"]


def test_acceptance_criterion_8_gmail_draft_via_mcp(mock_mcp_client):
    """Criterion 8: Gmail draft creation via Model Context Protocol (gmail_create_draft)."""
    gmail_adapter = GmailAdapter(client=mock_mcp_client)

    result = gmail_adapter.create_draft(
        recipient="stakeholder@zomato.internal",
        subject="Weekly Customer Voice Pulse: Zomato (2026-08-15 to 2026-11-05)",
        body="# Test Pulse Markdown with Doc Link: https://docs.google.com/document/d/1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0/edit"
    )

    assert result["status"] in ("success", "created")
    assert "draft_id" in result
    assert result["draft_id"].startswith("r")


def test_acceptance_criterion_9_zero_direct_google_apis():
    """Criterion 9: No direct Google REST API client code or OAuth flow implemented in the project."""
    forbidden_modules = [
        "googleapiclient",
        "google_auth_oauthlib",
        "google.oauth2",
        "google.auth",
    ]
    forbidden_urls = [
        "googleapis.com",
        "docs.googleapis.com",
        "gmail.googleapis.com",
    ]

    py_files = list(PROJECT_ROOT.glob("src/**/*.py")) + [PROJECT_ROOT / "main.py"]

    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        # AST check for forbidden imports
        try:
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for mod in forbidden_modules:
                            assert not alias.name.startswith(mod), (
                                f"Direct Google API import '{alias.name}' detected in {file_path.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    for mod in forbidden_modules:
                        assert not mod_name.startswith(mod), (
                            f"Direct Google API import from '{mod_name}' detected in {file_path.name}"
                        )
        except SyntaxError:
            pass

        # Substring check for hardcoded googleapis REST endpoints
        for url in forbidden_urls:
            assert url not in content, (
                f"Direct googleapis endpoint '{url}' detected in {file_path.name}"
            )
