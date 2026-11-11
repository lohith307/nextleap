"""
Google Docs MCP Adapter.
Publishes Weekly Pulse markdown documents via Google Docs MCP Server.
Saves local backup to Docs/generated_pulse.md so work is never lost.
Zero direct REST API calls.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from src.mcp_client.client import create_mcp_client

LOCAL_BACKUP_PATH = Path("Docs/generated_pulse.md")


class GoogleDocsAdapter:
    """
    Adapter invoking the Google Docs tool (create_document or append_to_doc) over MCP.
    """

    def __init__(self, client: Optional[Any] = None):
        self._client = client

    def create_document(
        self,
        title: str,
        content: str,
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls the Google Docs MCP server to publish or append the document.
        Always persists a local copy to Docs/generated_pulse.md.
        """
        # Always persist local copy first
        LOCAL_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_BACKUP_PATH, "w", encoding="utf-8") as f:
            f.write(content)

        client = self._client or create_mcp_client("google-docs")
        owns_client = self._client is None

        if owns_client:
            client.start()

        target_doc_id = (doc_id or os.getenv("GOOGLE_DOC_ID", "")).strip()

        try:
            result = client.call_tool(
                name="google_docs_create_document",
                arguments={
                    "title": title,
                    "content": content,
                    "doc_id": target_doc_id
                }
            )
            doc_id_res = result.get("document_id") or target_doc_id or "doc_unknown"
            doc_url = result.get("document_url") or f"https://docs.google.com/document/d/{doc_id_res}/edit"

            return {
                "document_id": doc_id_res,
                "document_url": doc_url,
                "local_backup_path": str(LOCAL_BACKUP_PATH),
                "raw_result": result,
                "status": result.get("status", "success")
            }
        except Exception as e:
            # Fallback when MCP fails: work is preserved locally at LOCAL_BACKUP_PATH
            doc_id_res = target_doc_id or "doc_fallback"
            return {
                "document_id": doc_id_res,
                "document_url": f"https://docs.google.com/document/d/{doc_id_res}/edit",
                "local_backup_path": str(LOCAL_BACKUP_PATH),
                "status": "local_fallback",
                "error": str(e)
            }
        finally:
            if owns_client:
                client.close()
