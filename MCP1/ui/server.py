"""
Lightweight Web Server and REST API for Zomato Customer Review Pulse UI.
Built purely with Python's standard library (http.server, json, urllib).
Zero external dependencies required.
"""
import os
import sys
import json
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ingestion.cache import load_sanitized_reviews
from src.clustering.ranking import run_thematic_clustering
from src.pipeline import CustomerVoicePulsePipeline

UI_DIR = ROOT_DIR / "ui"
DOCS_DIR = ROOT_DIR / "Docs"
REPORT_PATH = DOCS_DIR / "phases" / "phase-07" / "acceptance_report.json"
PULSE_PATH = DOCS_DIR / "generated_pulse.md"


class PulseUIRequestHandler(SimpleHTTPRequestHandler):
    """Handles static files from ui/ and JSON API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self._handle_get_status()
        elif path == "/api/pulse":
            self._handle_get_pulse()
        elif path == "/api/themes":
            self._handle_get_themes()
        elif path == "/api/reviews":
            self._handle_get_reviews(parse_qs(parsed.query))
        else:
            # Fall back to serving static files from ui/
            if path == "/" or not (UI_DIR / path.lstrip("/")).exists():
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            self._handle_post_run()
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_get_status(self):
        data = {
            "application": "com.application.zomato",
            "app_name": "Zomato: Food Delivery & Dining",
            "mcp_server": os.getenv("MCP_SERVER_URL", "https://web-production-45fffe.up.railway.app"),
            "doc_id": os.getenv("GOOGLE_DOC_ID", "1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0"),
            "doc_url": f"https://docs.google.com/document/d/{os.getenv('GOOGLE_DOC_ID', '1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0')}/edit",
            "recipient": os.getenv("STAKEHOLDER_RECIPIENT_EMAIL", "product-team@zomato.internal"),
            "status": "READY",
            "acceptance": None
        }
        if REPORT_PATH.exists():
            try:
                with open(REPORT_PATH, "r", encoding="utf-8") as f:
                    rep = json.load(f)
                    data["acceptance"] = rep.get("criteria_results")
                    data["pipeline_status"] = rep.get("pipeline_status")
                    data["last_run_timestamp"] = rep.get("timestamp")
                    data["draft_id"] = rep.get("draft_id")
            except Exception:
                pass
        self._send_json(data)

    def _handle_get_pulse(self):
        pulse_text = ""
        if PULSE_PATH.exists():
            pulse_text = PULSE_PATH.read_text(encoding="utf-8")

        # Parse sections
        themes = []
        quotes = []
        actions = []
        current_sec = None

        for line in pulse_text.splitlines():
            line_str = line.strip()
            if "### Top Themes" in line_str:
                current_sec = "themes"
            elif "### What Users Are Saying" in line_str:
                current_sec = "quotes"
            elif "### Action Ideas" in line_str:
                current_sec = "actions"
            elif line_str.startswith("#"):
                current_sec = None
            elif current_sec == "themes" and (line_str.startswith("1.") or line_str.startswith("2.") or line_str.startswith("3.")):
                themes.append(line_str)
            elif current_sec == "quotes" and (line_str.startswith("- *\"") or line_str.startswith("- \"") or line_str.startswith("- *'")):
                cleaned = line_str.lstrip("- *\"'").rstrip("*\"' ")
                quotes.append(cleaned)
            elif current_sec == "actions" and (line_str.startswith("1.") or line_str.startswith("2.") or line_str.startswith("3.")):
                actions.append(line_str)

        word_count = len([w for w in pulse_text.split() if any(c.isalnum() for c in w)])
        self._send_json({
            "markdown": pulse_text,
            "word_count": word_count,
            "word_limit": 250,
            "themes": themes,
            "quotes": quotes,
            "actions": actions
        })

    def _handle_get_themes(self):
        reviews = load_sanitized_reviews() or []
        res = run_thematic_clustering(reviews)
        clusters_data = []
        for c in res.all_clusters:
            clusters_data.append({
                "theme_id": c.theme_id,
                "name": c.name,
                "description": c.description,
                "review_count": c.review_count,
                "percentage_share": c.percentage_share,
                "negative_count": c.negative_count,
                "average_star_rating": c.average_star_rating,
                "severity_score": c.severity_score,
                "candidate_quotes": c.candidate_quotes[:3]
            })
        self._send_json({
            "reporting_period": res.reporting_period,
            "total_reviews": res.total_reviews_analyzed,
            "clusters": clusters_data
        })

    def _handle_get_reviews(self, query_params):
        reviews = load_sanitized_reviews() or []
        rating_filter = query_params.get("rating", [None])[0]
        search_query = query_params.get("q", [None])[0]
        limit = int(query_params.get("limit", [50])[0])

        filtered = reviews
        if rating_filter:
            try:
                r_val = int(rating_filter)
                filtered = [r for r in filtered if r.rating == r_val]
            except ValueError:
                pass

        if search_query:
            sq = search_query.lower()
            filtered = [r for r in filtered if sq in r.text.lower()]

        items = []
        for r in filtered[:limit]:
            items.append({
                "review_id": r.review_id,
                "rating": r.rating,
                "text": r.text,
                "date": r.date,
                "platform": r.platform,
                "thumbs_up": r.thumbs_up
            })

        self._send_json({
            "total_count": len(filtered),
            "returned_count": len(items),
            "reviews": items
        })

    def _handle_post_run(self):
        # Read request body
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        dry_run = req_data.get("dry_run", False)
        doc_id = req_data.get("doc_id", os.getenv("GOOGLE_DOC_ID", "1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0"))
        recipient = req_data.get("recipient", os.getenv("STAKEHOLDER_RECIPIENT_EMAIL", "product-team@zomato.internal"))

        pipeline = CustomerVoicePulsePipeline(recipient_email=recipient)
        result = pipeline.run(refresh_cache=False, dry_run=dry_run, doc_id=doc_id)

        self._send_json({
            "status": result.status,
            "reporting_period": result.date_range,
            "reviews_analyzed": result.total_reviews_analyzed,
            "document_url": result.document_url,
            "draft_id": result.draft_id,
            "word_count": result.pulse_report.word_count,
            "quote_veracity": result.pulse_report.quote_veracity_verified,
            "pii_clean": result.pulse_report.pii_free_verified,
            "pulse_markdown": result.pulse_report.weekly_pulse_markdown
        })


def run_server(port: int = 8000):
    UI_DIR.mkdir(parents=True, exist_ok=True)
    server_address = ("", port)
    httpd = HTTPServer(server_address, PulseUIRequestHandler)
    print(f"\n======================================================================")
    print(f"  ZOMATO CUSTOMER VOICE PULSE — INTERACTIVE WEB DASHBOARD")
    print(f"  Server running on http://localhost:{port}")
    print(f"  Press Ctrl+C to stop.")
    print(f"======================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)

