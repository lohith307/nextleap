"""
Standalone Mock MCP Server implementing JSON-RPC 2.0 over stdio.
Used for CI/testing and local execution without requiring live Google credentials.
Implements:
- initialize
- tools/list (GET /tools) exposing append_to_doc and create_email_draft schemas
- tools/call (append_to_doc, create_email_draft, google_docs_create_document, gmail_create_draft)
"""
import sys
import json
import time
import uuid

TOOLS = [
    {
        "name": "append_to_doc",
        "description": "Appends text content to the end of a specified Google Doc.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "Google Doc ID from document URL"
                },
                "content": {
                    "type": "string",
                    "description": "Text content to append"
                }
            },
            "required": ["doc_id", "content"]
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "Google Doc ID from document URL"
                },
                "content": {
                    "type": "string",
                    "description": "Text content to append"
                }
            },
            "required": ["doc_id", "content"]
        }
    },
    {
        "name": "create_email_draft",
        "description": "Creates a new email draft in Gmail with recipient, subject, and body.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["to", "subject", "body"]
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "google_docs_create_document",
        "description": "Creates a new Google Document with the given title and Markdown/plain text content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Markdown or text content of the document"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "gmail_create_draft",
        "description": "Creates a draft email in Gmail with recipient, subject, and body text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"}
            },
            "required": ["recipient", "subject", "body"]
        }
    }
]


def send_response(response_dict):
    """Sends JSON-RPC response to stdout and flushes immediately."""
    sys.stdout.write(json.dumps(response_dict) + "\n")
    sys.stdout.flush()


def handle_initialize(msg_id, params):
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "google-workspace-mcp-mock",
                "version": "1.0.0"
            }
        }
    }


def handle_tools_list(msg_id):
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {
            "tools": TOOLS
        }
    }


def handle_tools_call(msg_id, params):
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name in ("append_to_doc", "google_docs_create_document"):
        doc_id = arguments.get("doc_id") or f"1ZomatoPulse_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        title = arguments.get("title", "Review Doc")
        content = arguments.get("content", "")

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "success",
                            "document_id": doc_id,
                            "doc_id": doc_id,
                            "document_url": doc_url,
                            "title": title
                        })
                    }
                ],
                "document_id": doc_id,
                "doc_id": doc_id,
                "document_url": doc_url
            }
        }

    elif tool_name in ("create_email_draft", "gmail_create_draft"):
        draft_id = f"r-{int(time.time())}_{uuid.uuid4().hex[:6]}"
        recipient = arguments.get("to") or arguments.get("recipient", "")
        subject = arguments.get("subject", "")

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "created",
                            "draft_id": draft_id,
                            "recipient": recipient,
                            "subject": subject
                        })
                    }
                ],
                "draft_id": draft_id,
                "status": "created",
                "recipient": recipient,
                "subject": subject
            }
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Tool not found: {tool_name}"
            }
        }


def main():
    """Main loop reading JSON-RPC requests from stdin."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        msg_id = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            send_response(handle_initialize(msg_id, params))
        elif method == "notifications/initialized":
            pass
        elif method in ("tools/list", "get_tools", "tools"):
            send_response(handle_tools_list(msg_id))
        elif method == "tools/call":
            send_response(handle_tools_call(msg_id, params))
        elif method == "ping":
            send_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        else:
            if msg_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not supported: {method}"
                    }
                })


if __name__ == "__main__":
    main()
