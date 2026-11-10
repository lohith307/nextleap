# Phase 4: Model Context Protocol (MCP) Client & Google Workspace Adapters

## Overview
Phase 4 implements the Model Context Protocol (MCP) client layer that connects to Google Docs and Gmail MCP servers to deliver the weekly executive pulse. It adheres strictly to the **MCP-First rule: 100% of Google Workspace delivery is performed via MCP; zero direct REST API calls (`googleapis.com`) or manual OAuth flows exist in application code**.

---

## 1. Remote Railway MCP Server Specification

- **Server Endpoint:** `https://web-production-45fffe.up.railway.app`
- **Interactive Documentation:** `https://web-production-45fffe.up.railway.app/docs`
- **Architecture Reference:** [`google-mcp-server/docs_tool.py`](https://github.com/lohith307/google-mcp-server/blob/main/google-mcp-server/docs_tool.py)

### Discovered MCP Tools & Schemas (GET /tools):
`GET /tools` on the MCP server returns the full JSON schemas for `append_to_doc` and `create_email_draft`:

```json
{
  "tools": [
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
      }
    }
  ]
}
```

---

## 2. Configuration & Secrets ([`.env`](file:///c:/Users/lohith%20k/MCP1/.env))

```env
# Stakeholder delivery configuration (for Gmail MCP draft)
STAKEHOLDER_RECIPIENT_EMAIL=product-team@zomato.internal

# Remote Model Context Protocol (MCP) Server deployed on Railway
MCP_SERVER_URL=https://web-production-45fffe.up.railway.app

# Google Doc ID to append pulse report
GOOGLE_DOC_ID=1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0
```

---

## 3. Adapters & Code Structure

| Component | File Path | Role |
|---|---|---|
| **MCP Client Manager** | [`src/mcp_client/client.py`](file:///c:/Users/lohith%20k/MCP1/src/mcp_client/client.py) | Manages `RemoteHttpMCPClient` (Railway) and `StdioMCPClient` (local JSON-RPC 2.0). |
| **Google Docs Adapter** | [`src/mcp_client/docs_adapter.py`](file:///c:/Users/lohith%20k/MCP1/src/mcp_client/docs_adapter.py) | Calls `append_to_doc` via MCP and saves local backup to `Docs/generated_pulse.md`. |
| **Gmail Adapter** | [`src/mcp_client/gmail_adapter.py`](file:///c:/Users/lohith%20k/MCP1/src/mcp_client/gmail_adapter.py) | Calls `create_email_draft` via MCP with recipient dynamically loaded from `.env`. |
| **Phase 4 CLI Runner** | [`run_phase4.py`](file:///c:/Users/lohith%20k/MCP1/run_phase4.py) | Dedicated executable script verifying tools discovery, Docs append, and Gmail draft creation. |
| **Test Suite** | [`tests/test_mcp_client.py`](file:///c:/Users/lohith%20k/MCP1/tests/test_mcp_client.py) | Tests stdio handshake, remote tools discovery, env fallback, and 0 direct REST APIs. |

---

## 4. Execution Output (`python run_phase4.py`)

```text
=====================================================================================
  PHASE 4: MODEL CONTEXT PROTOCOL (MCP) CLIENT & WORKSPACE ADAPTERS
  Connecting to MCP Server: web-production-45fffe.up.railway.app
=====================================================================================

[INFO] MCP Server URL:        https://web-production-45fffe.up.railway.app
[INFO] Configured Google Doc ID: 1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0
[INFO] Stakeholder Recipient:   product-team@zomato.internal

[INFO] Loaded synthesized pulse from Docs\generated_pulse.md (244 words)

-------------------------------------------------------------------------------------
  STEP 1: DISCOVER MCP TOOLS
-------------------------------------------------------------------------------------
  Discovered 2 tools on MCP server:
  • append_to_doc             - Appends text content to the end of a specified Google Doc.
  • create_email_draft        - Creates a new email draft in Gmail with recipient, subject, and body.

-------------------------------------------------------------------------------------
  STEP 2: PUBLISH TO GOOGLE DOCS VIA MCP
-------------------------------------------------------------------------------------
  Invoking MCP tool to append pulse to Google Doc (ID: 1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0)...
  [SUCCESS] Google Doc Published via MCP:
            Document URL: https://docs.google.com/document/d/1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0/edit
            Local Backup: Docs\generated_pulse.md

-------------------------------------------------------------------------------------
  STEP 3: CREATE GMAIL DRAFT VIA MCP
-------------------------------------------------------------------------------------
  Invoking MCP tool to create Gmail draft for 'product-team@zomato.internal'...
  [SUCCESS] Gmail Draft Created via MCP:
            Draft ID:  r-5143818851047101669
            Recipient: product-team@zomato.internal
            Subject:   Weekly Customer Voice Pulse: Zomato (Latest Synthesis)

=====================================================================================
  PHASE 4 EXECUTION SUMMARY & INVARIANT AUDIT
=====================================================================================
  • MCP Server Endpoint:      https://web-production-45fffe.up.railway.app
  • Google Docs Delivery:     SUCCESS (https://docs.google.com/document/d/1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0/edit)
  • Gmail Draft Delivery:     SUCCESS (Draft ID: r-5143818851047101669)
  • Stakeholder Recipient:    product-team@zomato.internal (Loaded from .env)
  • Zero Direct Google APIs:  VERIFIED (100% routed through MCP)
=====================================================================================
```

---

## 5. Test Suite Verification
Running:
```powershell
python -m pytest tests/test_mcp_client.py -v
```
Output:
```text
tests/test_mcp_client.py::test_mcp_handshake_and_tools_list PASSED       [ 14%]
tests/test_mcp_client.py::test_get_tools_schema_definitions PASSED       [ 28%]
tests/test_mcp_client.py::test_google_docs_mcp_adapter PASSED            [ 42%]
tests/test_mcp_client.py::test_gmail_mcp_adapter PASSED                  [ 57%]
tests/test_mcp_client.py::test_gmail_adapter_uses_env_recipient PASSED   [ 71%]
tests/test_mcp_client.py::test_remote_http_mcp_client_tools PASSED       [ 85%]
tests/test_mcp_client.py::test_zero_direct_rest_apis_check PASSED        [100%]

============================== 7 passed in 6.30s ==============================
```

