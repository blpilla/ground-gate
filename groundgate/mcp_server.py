"""Minimal MCP server over stdio — zero dependencies.

Implements the subset of the Model Context Protocol needed to expose the
gate as a tool: ``initialize``, ``ping``, ``tools/list`` and ``tools/call``
over JSON-RPC 2.0, newline-delimited on stdin/stdout.

Run with:  ``groundgate mcp``  or  ``python -m groundgate.mcp_server``

Claude Desktop / any MCP client config:

    {
      "mcpServers": {
        "groundgate": {"command": "groundgate", "args": ["mcp"]}
      }
    }
"""

from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .gate import GroundGate

PROTOCOL_VERSION = "2025-06-18"

TOOL_DEFINITION = {
    "name": "verify_grounding",
    "description": (
        "Verify claim-by-claim whether a RAG answer is supported by its "
        "retrieved context. Returns pass/fail plus a structured per-claim "
        "breakdown (claim, supported, source_span, confidence, reason). "
        "Use it as a gate before showing a RAG answer to the user: on "
        "'fail', block the answer or re-retrieve."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The generated answer to verify.",
            },
            "context": {
                "description": (
                    "Retrieved context: a string, a list of strings, or a "
                    "list of {id, text} objects (ids enable citation checks)."
                ),
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                    },
                ],
            },
            "require_citations": {
                "type": "boolean",
                "description": "Fail claims that carry no citation marker.",
                "default": False,
            },
        },
        "required": ["answer", "context"],
    },
}


def _result(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(request: dict, gate: GroundGate | None = None) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications."""
    method = request.get("method", "")
    request_id = request.get("id")

    if method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "groundgate", "version": __version__},
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": [TOOL_DEFINITION]})
    if method == "tools/call":
        params = request.get("params") or {}
        if params.get("name") != "verify_grounding":
            return _error(request_id, -32602, f"unknown tool: {params.get('name')!r}")
        arguments = params.get("arguments") or {}
        try:
            active_gate = gate or GroundGate(
                require_citations=bool(arguments.get("require_citations", False))
            )
            verdict = active_gate.verify(arguments["answer"], arguments["context"])
        except (KeyError, TypeError) as exc:
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": f"invalid arguments: {exc}"}],
                    "isError": True,
                },
            )
        payload = verdict.to_dict()
        return _result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                    }
                ],
                "structuredContent": payload,
                "isError": False,
            },
        )

    return _error(request_id, -32601, f"method not found: {method}")


def serve(stdin=None, stdout=None, gate: GroundGate | None = None) -> None:
    """Blocking stdio loop: one JSON-RPC message per line."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response: dict | None = _error(None, -32700, "parse error")
        else:
            response = handle_request(request, gate=gate)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
