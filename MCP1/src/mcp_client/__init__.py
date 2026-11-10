"""
MCP Client module for Zomato Customer Review Pulse pipeline.
"""
from src.mcp_client.client import (
    StdioMCPClient,
    RemoteHttpMCPClient,
    MCPError,
    create_mcp_client,
    load_mcp_server_config,
)
from src.mcp_client.docs_adapter import GoogleDocsAdapter
from src.mcp_client.gmail_adapter import GmailAdapter

__all__ = [
    "StdioMCPClient",
    "RemoteHttpMCPClient",
    "MCPError",
    "create_mcp_client",
    "load_mcp_server_config",
    "GoogleDocsAdapter",
    "GmailAdapter",
]
