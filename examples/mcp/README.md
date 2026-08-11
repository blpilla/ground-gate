# GroundGate as an MCP server

GroundGate ships a zero-dependency MCP server (stdio transport) exposing one
tool, `verify_grounding`. Any MCP-capable agent — Claude Desktop, Claude Code,
or your own agent loop — can call it as a gate before delivering RAG answers.

## Claude Desktop / Claude Code configuration

Add to `claude_desktop_config.json` (or `.mcp.json` for Claude Code):

```json
{
  "mcpServers": {
    "groundgate": {
      "command": "groundgate",
      "args": ["mcp"]
    }
  }
}
```

A ready-to-copy file is in [`config.json`](config.json). If the package is not
on PATH, use `python -m groundgate.mcp_server` as the command instead.

## Tool contract

Request arguments:

| argument            | type                                   | description                              |
| ------------------- | -------------------------------------- | ---------------------------------------- |
| `answer`            | string                                 | The generated answer to verify.          |
| `context`           | string \| string[] \| {id, text}[]     | Retrieved chunks; ids enable citation checks. |
| `require_citations` | boolean (default false)                | Fail claims with no citation marker.     |

Response (`structuredContent`):

```json
{
  "status": "fail",
  "passed": false,
  "score": 0.5,
  "reasons": ["unsupported claim: '...' (numbers not found in source: 12)"],
  "claims": [
    {
      "claim": "A carencia e de 12 horas.",
      "citations": ["1"],
      "supported": false,
      "confidence": 0.9,
      "reason": "numbers not found in source: 12",
      "method": "deterministic",
      "source_span": {"source_id": "1", "start": 0, "end": 58, "text": "..."}
    }
  ]
}
```

## Smoke test without a client

The transport is newline-delimited JSON-RPC on stdio:

```bash
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"verify_grounding","arguments":{"answer":"A carencia e de 12 horas.","context":"A carencia do plano e de 24 horas."}}}' \
  | groundgate mcp
```
