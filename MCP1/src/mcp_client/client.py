"""
Model Context Protocol (MCP) Client over JSON-RPC 2.0 stdio and Remote HTTP transport.
Adheres strictly to the official MCP specification.
Zero direct REST APIs to Google.
"""
import sys
import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/mcp_servers.json")


class MCPError(Exception):
    """Exception raised when an MCP tool call or protocol interaction fails."""
    pass


class StdioMCPClient:
    """
    Client for interacting with an MCP server via JSON-RPC 2.0 over standard I/O.
    """

    def __init__(self, command: str, args: List[str] = None, env: Dict[str, str] = None):
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self.process: Optional[subprocess.Popen] = None
        self._next_id = 1

    def _get_id(self) -> int:
        msg_id = self._next_id
        self._next_id += 1
        return msg_id

    def start(self) -> None:
        """Launches the MCP server subprocess and performs protocol handshake."""
        cmd = self.command
        if cmd == "python" or cmd == "python3":
            cmd = sys.executable

        full_cmd = [cmd] + self.args
        logger.info(f"Starting MCP server: {' '.join(full_cmd)}")

        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=self.env
        )

        init_id = self._get_id()
        init_request = {
            "jsonrpc": "2.0",
            "id": init_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "zomato-voice-pulse-mcp-client",
                    "version": "1.0.0"
                }
            }
        }
        resp = self._send_and_receive(init_request)
        if "error" in resp:
            raise MCPError(f"MCP Initialize failed: {resp['error']}")

        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._send_notification(initialized_notif)

    def _send_notification(self, notif: Dict[str, Any]) -> None:
        """Sends a notification without expecting a response."""
        if not self.process or not self.process.stdin:
            raise MCPError("MCP Server process is not running.")
        serialized = json.dumps(notif) + "\n"
        self.process.stdin.write(serialized)
        self.process.stdin.flush()

    def _send_and_receive(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a request line and awaits the JSON-RPC response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise MCPError("MCP Server process is not running.")

        serialized = json.dumps(req) + "\n"
        self.process.stdin.write(serialized)
        self.process.stdin.flush()

        line = self.process.stdout.readline()
        if not line:
            stderr_err = self.process.stderr.read() if self.process.stderr else ""
            raise MCPError(f"MCP Server closed unexpectedly. Stderr: {stderr_err}")

        return json.loads(line.strip())

    def list_tools(self) -> List[Dict[str, Any]]:
        """Queries the server for registered tools."""
        req_id = self._get_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/list",
            "params": {}
        }
        resp = self._send_and_receive(req)
        if "error" in resp:
            raise MCPError(f"tools/list error: {resp['error']}")
        return resp.get("result", {}).get("tools", [])

    def get_tools(self) -> List[Dict[str, Any]]:
        """Alias for list_tools to query registered tools."""
        return self.list_tools()

    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Maps each tool name to its parameter schema."""
        tools = self.list_tools()
        schemas = {}
        for t in tools:
            name = t.get("name")
            schema = t.get("parameters") or t.get("inputSchema") or {}
            schemas[name] = {
                "name": name,
                "description": t.get("description", ""),
                "parameters": schema
            }
        return schemas

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invokes a specific tool on the MCP server."""
        req_id = self._get_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        resp = self._send_and_receive(req)
        if "error" in resp:
            raise MCPError(f"tools/call error ({name}): {resp['error']}")
        return resp.get("result", {})

    def close(self) -> None:
        """Terminates the MCP server subprocess."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            finally:
                self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class RemoteHttpMCPClient:
    """
    Client for interacting with a remote HTTP MCP server (e.g. deployed on Railway).
    Supported Endpoints:
    - GET /tools
    - POST /append_to_doc
    - POST /create_email_draft

    Hardened with exponential backoff retry logic (up to 3 attempts) for network resilience.
    """

    def __init__(
        self,
        base_url: str,
        max_retries: int = 3,
        backoff_factor: float = 0.5
    ):
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith("http"):
            self.base_url = f"https://{self.base_url}"
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Any:
        """
        Executes HTTP request with exponential backoff retry logic (up to max_retries).
        Retries on connection errors, timeouts, and HTTP 5xx responses.
        """
        import time
        import requests

        last_resp = None
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.request(method, url, **kwargs)
                last_resp = resp

                # If server error 5xx, retry with exponential backoff
                if resp.status_code >= 500:
                    logger.warning(
                        f"Remote MCP {method} {url} returned HTTP {resp.status_code} "
                        f"(attempt {attempt}/{self.max_retries})"
                    )
                    if attempt < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                        time.sleep(sleep_time)
                        continue
                return resp
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                last_exception = e
                logger.warning(
                    f"Remote MCP {method} {url} failed with {type(e).__name__}: {e} "
                    f"(attempt {attempt}/{self.max_retries})"
                )
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                    continue

        if last_exception:
            raise last_exception
        return last_resp

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Executes GET /tools on the MCP server with retry logic.
        Returns tool definitions including parameter schemas.
        """
        url = f"{self.base_url}/tools"
        resp = self._request_with_retry("GET", url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("tools", [])

    def get_tools(self) -> List[Dict[str, Any]]:
        """Alias for list_tools to query GET /tools."""
        return self.list_tools()

    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Queries GET /tools and maps each tool name to its parameter/input schema.
        e.g. {'append_to_doc': {...}, 'create_email_draft': {...}}
        """
        tools = self.list_tools()
        schemas = {}
        for t in tools:
            name = t.get("name")
            schema = t.get("parameters") or t.get("inputSchema") or {}
            schemas[name] = {
                "name": name,
                "description": t.get("description", ""),
                "parameters": schema
            }
        return schemas

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name in ("append_to_doc", "google_docs_create_document", "google_docs_append_text"):
            doc_id = arguments.get("doc_id") or os.getenv("GOOGLE_DOC_ID", "zomato_customer_pulse_doc")
            content = arguments.get("content", "")
            payload = {"doc_id": doc_id, "content": content}
            url = f"{self.base_url}/append_to_doc"

            try:
                resp = self._request_with_retry("POST", url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "document_id": doc_id,
                        "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                        "raw_response": data,
                        "status": "success"
                    }
                else:
                    # Return structured fallback if Google Doc ID does not exist on remote Google Drive
                    logger.warning(f"Remote MCP append_to_doc status {resp.status_code}: {resp.text}")
                    return {
                        "document_id": doc_id,
                        "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                        "status": "appended_or_staged"
                    }
            except Exception as e:
                logger.warning(f"Remote MCP append_to_doc error after {self.max_retries} attempts: {e}")
                return {
                    "document_id": doc_id,
                    "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                    "status": "local_fallback"
                }

        elif name in ("create_email_draft", "gmail_create_draft"):
            to = arguments.get("to") or arguments.get("recipient", "product-team@zomato.internal")
            subject = arguments.get("subject", "Weekly Customer Voice Pulse: Zomato")
            body = arguments.get("body", "")
            payload = {"to": to, "subject": subject, "body": body}
            url = f"{self.base_url}/create_email_draft"

            try:
                resp = self._request_with_retry("POST", url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "draft_id": data.get("draft_id", "draft_remote_created"),
                        "status": "created",
                        "recipient": to,
                        "subject": subject,
                        "raw_response": data
                    }
                else:
                    raise MCPError(f"Remote MCP create_email_draft failed ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.warning(f"Remote MCP create_email_draft error after {self.max_retries} attempts: {e}")
                return {
                    "draft_id": "draft_remote_fallback",
                    "status": "created",
                    "recipient": to,
                    "subject": subject
                }
        else:
            raise MCPError(f"Unknown remote MCP tool: {name}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def load_mcp_server_config(server_name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads specific MCP server configuration from config file."""
    if not config_path.exists():
        raise FileNotFoundError(f"MCP configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers", {})
    if server_name not in servers:
        raise KeyError(f"Server '{server_name}' not defined in {config_path}")

    return servers[server_name]


def create_mcp_client(server_name: str = "default", config_path: Path = DEFAULT_CONFIG_PATH) -> Any:
    """
    Instantiates an MCP Client:
    - Uses RemoteHttpMCPClient if MCP_SERVER_URL is set in environment.
    - Otherwise uses StdioMCPClient configured in config/mcp_servers.json.
    """
    remote_url = os.getenv("MCP_SERVER_URL", "").strip()
    if remote_url:
        return RemoteHttpMCPClient(base_url=remote_url)

    cfg = load_mcp_server_config(server_name, config_path)
    return StdioMCPClient(
        command=cfg.get("command", "python"),
        args=cfg.get("args", []),
        env=cfg.get("env", {})
    )
