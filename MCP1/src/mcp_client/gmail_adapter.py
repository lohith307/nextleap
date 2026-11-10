"""
Gmail MCP Adapter.
Creates draft emails to stakeholders via Gmail MCP Server with links to the generated pulse Google Doc.
Zero direct REST API calls.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from src.mcp_client.client import create_mcp_client


class GmailAdapter:
    """
    Adapter invoking the Gmail draft creation tool over MCP protocol.
    """

    def __init__(self, client: Optional[Any] = None):
        self._client = client

    def create_draft(
        self,
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls Gmail MCP server to create an email draft.
        Recipient is resolved from argument or STAKEHOLDER_RECIPIENT_EMAIL in .env.
        """
        target_recipient = (
            recipient
            or os.getenv("STAKEHOLDER_RECIPIENT_EMAIL")
            or os.getenv("RECIPIENT_EMAIL")
            or "product-team@zomato.internal"
        ).strip()
        target_subject = subject or "Weekly Customer Voice Pulse: Zomato"
        target_body = body or ""

        client = self._client or create_mcp_client("gmail")
        owns_client = self._client is None

        if owns_client:
            client.start()

        try:
            result = client.call_tool(
                name="gmail_create_draft",
                arguments={
                    "recipient": target_recipient,
                    "to": target_recipient,
                    "subject": target_subject,
                    "body": target_body
                }
            )
            draft_id = result.get("draft_id") or "draft_unknown"
            status = result.get("status") or "created"

            return {
                "draft_id": draft_id,
                "status": status,
                "recipient": target_recipient,
                "subject": target_subject,
                "raw_result": result
            }
        finally:
            if owns_client:
                client.close()
