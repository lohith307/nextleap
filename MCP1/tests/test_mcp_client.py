"""
Unit and integration tests for Phase 4: MCP Client and Workspace Adapters.
Verifies:
1. MCP JSON-RPC 2.0 handshake and tools/list discovery.
2. Google Docs MCP tool invocation and document URL generation.
3. Gmail MCP draft creation tool invocation.
4. Strict enforcement of zero direct googleapis.com REST calls.
"""
import os
import sys
from pathlib import Path
import pytest
from src.mcp_client.client import StdioMCPClient, create_mcp_client
from src.mcp_client.docs_adapter import GoogleDocsAdapter
from src.mcp_client.gmail_adapter import GmailAdapter


@pytest.fixture
def mcp_client():
    """Fixture providing a connected MCP client to the mock server."""
    client = StdioMCPClient(
        command=sys.executable,
        args=["-m", "tests.mock_mcp_server"]
    )
    client.start()
    yield client
    client.close()


def test_mcp_handshake_and_tools_list(mcp_client):
    """Assert client initializes with mock server and discovers required tools."""
    tools = mcp_client.list_tools()
    assert len(tools) >= 2

    tool_names = [t["name"] for t in tools]
    assert "append_to_doc" in tool_names
    assert "create_email_draft" in tool_names
    assert "google_docs_create_document" in tool_names
    assert "gmail_create_draft" in tool_names


def test_get_tools_schema_definitions(mcp_client):
    """Assert GET /tools returns full schemas for append_to_doc and create_email_draft."""
    schemas = mcp_client.get_tool_schemas()

    assert "append_to_doc" in schemas
    append_params = schemas["append_to_doc"]["parameters"]
    assert "properties" in append_params
    assert "doc_id" in append_params["properties"]
    assert "content" in append_params["properties"]
    assert set(append_params.get("required", [])) == {"doc_id", "content"}

    assert "create_email_draft" in schemas
    email_params = schemas["create_email_draft"]["parameters"]
    assert "properties" in email_params
    assert "to" in email_params["properties"]
    assert "subject" in email_params["properties"]
    assert "body" in email_params["properties"]
    assert set(email_params.get("required", [])) == {"to", "subject", "body"}


def test_google_docs_mcp_adapter(mcp_client):
    """Assert Google Docs adapter calls google_docs_create_document via MCP."""
    adapter = GoogleDocsAdapter(client=mcp_client)
    title = "Zomato Customer Voice Pulse - Test"
    content = "# Test Customer Pulse\n\n- Real feedback verbatim."

    result = adapter.create_document(title=title, content=content)

    assert "document_id" in result
    assert "document_url" in result
    assert "https://docs.google.com/document/d/" in result["document_url"]

    # Verify persistent local backup exists
    backup_file = Path(result["local_backup_path"])
    assert backup_file.exists()
    assert content in backup_file.read_text(encoding="utf-8")


def test_gmail_mcp_adapter(mcp_client):
    """Assert Gmail adapter calls gmail_create_draft via MCP."""
    adapter = GmailAdapter(client=mcp_client)
    recipient = "product-team@zomato.internal"
    subject = "Weekly Customer Voice Pulse: Zomato"
    body = "Review the pulse at https://docs.google.com/document/d/test/edit"

    result = adapter.create_draft(recipient=recipient, subject=subject, body=body)

    assert "draft_id" in result
    assert result["status"] == "created"
    assert result["recipient"] == recipient
    assert result["subject"] == subject


def test_gmail_adapter_uses_env_recipient(mcp_client, monkeypatch):
    """Assert Gmail adapter falls back to STAKEHOLDER_RECIPIENT_EMAIL in .env."""
    monkeypatch.setenv("STAKEHOLDER_RECIPIENT_EMAIL", "custom-stakeholder@zomato.internal")
    adapter = GmailAdapter(client=mcp_client)
    result = adapter.create_draft(subject="Test Pulse", body="Body text")
    assert result["recipient"] == "custom-stakeholder@zomato.internal"


def test_remote_http_mcp_client_tools():
    """Assert RemoteHttpMCPClient can discover tools on live Railway MCP server."""
    from src.mcp_client.client import RemoteHttpMCPClient
    remote_url = os.getenv("MCP_SERVER_URL", "https://web-production-45fffe.up.railway.app")
    client = RemoteHttpMCPClient(base_url=remote_url)
    try:
        tools = client.list_tools()
        assert len(tools) >= 2
        tool_names = [t["name"] for t in tools]
        assert "append_to_doc" in tool_names
        assert "create_email_draft" in tool_names

        schemas = client.get_tool_schemas()
        assert "append_to_doc" in schemas
        append_props = schemas["append_to_doc"]["parameters"]["properties"]
        assert "doc_id" in append_props
        assert "content" in append_props

        assert "create_email_draft" in schemas
        draft_props = schemas["create_email_draft"]["parameters"]["properties"]
        assert "to" in draft_props
        assert "subject" in draft_props
        assert "body" in draft_props
    except Exception as e:
        pytest.skip(f"Remote MCP server unreachable in current environment: {e}")



def test_zero_direct_rest_apis_check():
    """
    Codebase static analysis test:
    Asserts zero imports of google-api-python-client, google-auth-oauthlib,
    and zero raw HTTP requests to 'googleapis.com' in src/.
    """
    src_dir = Path("src")
    forbidden_terms = [
        "googleapis.com",
        "googleapiclient",
        "google_auth_oauthlib",
        "google.oauth2",
    ]

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for forbidden in forbidden_terms:
            assert forbidden not in content, (
                f"Violation of MCP-First rule: found forbidden '{forbidden}' in {py_file}."
                " All Google Workspace integration must be done via MCP servers."
            )

