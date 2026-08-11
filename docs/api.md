# API reference

Everything public lives in the top-level `groundgate` package; provider
judges live in `groundgate.providers`.

## `verify(answer, context, **gate_kwargs) -> Verdict`

One-line entry point. Builds a `GroundGate` from the keyword arguments (or
reuses a shared deterministic, fail-closed gate when none are given) and
verifies the answer.

```python
from groundgate import verify

verdict = verify(answer, context)
verdict = verify(answer, context, require_citations=True)
```

**`answer`** — the generated text to verify.

**`context`** — what your retriever returned. Accepted shapes:

| shape                         | source ids                    |
| ----------------------------- | ----------------------------- |
| `str`                         | single source with id `"1"`   |
| `list[str]`                   | positional ids `"1"`, `"2"`…  |
| `list[dict]` (`{id?, text}`)  | your ids (enables citations)  |
| `list[Source]`                | your ids                      |

## `GroundGate(judge=None, require_citations=False, fail_open=False)`

The configurable gate. Reuse one instance across requests.

- **`judge`** — optional LLM judge consulted only for *ambiguous* claims
  (partial token overlap). Any object with
  `judge(claim: str, evidence: str) -> JudgeResult` works.
- **`require_citations`** — when `True`, claims without a citation marker
  fail (`method="citation"`). Recommended for regulated domains.
- **`fail_open`** — when `True`, ambiguous claims with no judge configured
  pass instead of failing. Default `False` (fail-closed).

### `GroundGate.verify(answer, context) -> Verdict`

Pipeline per claim:

1. **Citation check** — citations to unknown source ids fail immediately;
   cited claims are matched *only* against their cited sources.
2. **Deterministic match** — verbatim containment → supported; high
   token-window coverage (≥ 0.7) → supported; low coverage (< 0.4) or any
   claim number absent from the source → unsupported; in between → ambiguous.
3. **Judge escalation** — ambiguous claims go to `judge` if configured,
   otherwise the `fail_open` policy applies.

## Types

### `Verdict`

| member               | type                    | meaning                                  |
| -------------------- | ----------------------- | ---------------------------------------- |
| `passed`             | `bool`                  | every claim supported                    |
| `status`             | `"pass" \| "fail"`      | string form of `passed`                  |
| `score`              | `float`                 | fraction of supported claims             |
| `claims`             | `tuple[ClaimVerdict]`   | per-claim breakdown                      |
| `unsupported_claims` | `tuple[ClaimVerdict]`   | just the failures                        |
| `reasons`            | `tuple[str]`            | one line per failure                     |
| `to_dict()`          | `dict`                  | stable wire format (MCP/CLI/HTTP)        |

### `ClaimVerdict`

`claim`, `supported`, `confidence` (0–1), `reason`,
`method` (`"deterministic" | "judge" | "citation" | "policy"`),
`source_span` (`Span | None` — the passage that supports, or best matches,
the claim).

### `Span`

`source_id`, `start`, `end` (character offsets), `text`.

### `Claim`

`text` (citation markers stripped), `citations` (tuple of source ids).

### `JudgeResult`

`supported: bool`, `confidence: float`, `reason: str`.

## Judges — `groundgate.providers`

| class            | backend                        | install                        |
| ---------------- | ------------------------------ | ------------------------------ |
| `AnthropicJudge` | Anthropic API                  | `pip install groundgate[anthropic]` |
| `OpenAIJudge`    | OpenAI / OpenAI-compatible     | `pip install groundgate[openai]`    |
| `BedrockJudge`   | AWS Bedrock (Converse API)     | `pip install groundgate[bedrock]`   |
| `OllamaJudge`    | local Ollama (stdlib HTTP)     | nothing extra                  |

Each accepts `model=...` and either a pre-built `client` or client kwargs.
All judges parse a strict-JSON reply and **fail closed** on unparseable
output.

## MCP server

`groundgate mcp` (or `python -m groundgate.mcp_server`) serves newline-
delimited JSON-RPC 2.0 on stdio, exposing the `verify_grounding` tool.
Arguments mirror `verify`: `answer`, `context`, `require_citations`. The
verdict is returned both as pretty-printed text content and as
`structuredContent`. See [`examples/mcp/`](../examples/mcp/).

## CLI

```
groundgate verify --answer TEXT --context TEXT_OR_FILE [--require-citations]
groundgate mcp
```

`--context` accepts inline text, a `.txt` file, or a `.json` file with a list
of `{id, text}` sources. Prints the JSON verdict; exits 1 on fail.
