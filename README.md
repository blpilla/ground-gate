# GroundGate

**Runtime faithfulness gate for RAG.** Verifies, claim by claim, whether a
generated answer is actually supported by the retrieved context — and blocks
it (or triggers re-retrieval) *before* it reaches the user.

[![CI](https://github.com/blpilla/groundgate/actions/workflows/ci.yml/badge.svg)](https://github.com/blpilla/groundgate/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## The problem

Production RAG systems hallucinate even when retrieval is correct. The
expensive failure mode is the **citation that doesn't hold**: the answer looks
grounded — it even cites a source — but the cited passage doesn't support the
claim. In regulated domains (health, insurance, legal, finance) that is
material risk, not a cosmetic bug.

Evaluation frameworks (RAGAS, TruLens, DeepEval) measure this **offline**, in
batch. GroundGate is the missing piece: a **gate at runtime**, in the request
path, answering one question per claim — *does this sentence come from this
passage of this source?*

## Quickstart

```bash
pip install groundgate
```

```python
from groundgate import verify

verdict = verify(answer, context)   # one line; no LLM required

if not verdict.passed:
    for claim in verdict.unsupported_claims:
        print(claim.claim.text, "→", claim.reason)
    # block the answer, regenerate, or re-retrieve
```

`context` can be a string, a list of strings, or `[{"id": ..., "text": ...}]`
chunks — ids enable citation checking (`[1]`, `[policy]`, `(fonte: faq)`).

Every claim gets a structured, explainable verdict:

```json
{
  "claim": "A carencia para emergencias e de 12 horas.",
  "citations": ["policy"],
  "supported": false,
  "confidence": 0.9,
  "reason": "numbers not found in source: 12",
  "method": "deterministic",
  "source_span": {"source_id": "policy", "start": 0, "end": 74, "text": "..."}
}
```

## How it works

```
answer + retrieved context
        │
        ▼
  claim decomposition (deterministic sentence-level split + citation extraction)
        │
        ▼
  citation check ──── cited source unknown? → fail
        │
        ▼
  deterministic matcher ── verbatim containment, token-window coverage,
        │                  number consistency (limits, deadlines, amounts)
        │
        ├─ supported / unsupported → done, zero LLM cost
        ▼
  ambiguous only → LLM-as-judge (optional, provider-agnostic)
        │
        ▼
  Verdict: pass/fail + per-claim reasons → your app decides
```

**Determinism first.** Most claims are decided by cheap, flicker-free checks.
Only genuinely ambiguous paraphrases escalate to a judge. With no judge
configured, the gate **fails closed** (configurable via `fail_open=True`).

## LLM judges (optional)

```python
from groundgate import GroundGate
from groundgate.providers import AnthropicJudge, OpenAIJudge, OllamaJudge, BedrockJudge

gate = GroundGate(judge=AnthropicJudge())            # pip install groundgate[anthropic]
gate = GroundGate(judge=OpenAIJudge())               # pip install groundgate[openai]
gate = GroundGate(judge=BedrockJudge())              # pip install groundgate[bedrock]
gate = GroundGate(judge=OllamaJudge("llama3.1"))     # local, zero extra deps
```

Any object with a `judge(claim, evidence) -> JudgeResult` method works —
never locked to a provider, fully self-hostable, no data leaves your stack
unless you choose a hosted judge.

## MCP server

GroundGate is MCP-native: a zero-dependency stdio server exposes the gate as
a `verify_grounding` tool for any agent (Claude Desktop, Claude Code, custom
loops):

```json
{
  "mcpServers": {
    "groundgate": {"command": "groundgate", "args": ["mcp"]}
  }
}
```

See [`examples/mcp/`](examples/mcp/) for the tool contract and a smoke test.

## CLI

```bash
groundgate verify --answer "A carencia e de 12 horas." \
                  --context policy.txt
# → JSON verdict on stdout; exit code 1 on fail (CI-friendly)
```

## Strictness knobs

```python
GroundGate(
    judge=None,               # optional LLM judge for ambiguous claims
    require_citations=True,   # uncited claims fail (regulated-domain mode)
    fail_open=False,          # keep False in health/insurance/legal
)
```

## Examples

- [`examples/quickstart.py`](examples/quickstart.py) — first verdict in 30 seconds.
- [`examples/quickstart.ipynb`](examples/quickstart.ipynb) — notebook walkthrough.
- [`examples/rag_gate_loop.py`](examples/rag_gate_loop.py) — the production
  pattern: verify → block → regenerate/re-retrieve.
- [`examples/mcp/`](examples/mcp/) — plugging the gate into MCP agents.

The test suite ships paired faithful/unfaithful cases from the anchor domain
(Brazilian health & insurance policies): [`tests/data/insurance_pairs.json`](tests/data/insurance_pairs.json).

## Design principles

- **One-line integration** — `verify(answer, context)`; under 5 minutes to first verdict.
- **Composable piece, not a platform** — plugs into your stack; doesn't replace it.
- **Provider-agnostic** — OpenAI, Anthropic, Bedrock, Ollama, or none at all.
- **Self-hostable / privacy-first** — the deterministic core never makes a network call.
- **Zero runtime dependencies** — the core is pure standard library.

## Benchmark

A reproducible benchmark against naive baselines on paired
faithful/unfaithful RAG answers from regulated domains lives in
[`benchmark/`](benchmark/) — run `python benchmark/run.py` to regenerate
[`benchmark/RESULTS.md`](benchmark/RESULTS.md).

## Documentation

- [`docs/api.md`](docs/api.md) — full API reference.
- [`docs/launch-post.md`](docs/launch-post.md) — the "why", with numbers.
- [`ROADMAP.md`](ROADMAP.md) — where the project is going.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, tests, release process.

## Project status

v0.1 (alpha). The runtime gate (SDK, MCP server, CLI) is complete and tested.
Out of scope for now: dashboards, multimodal, observability integrations —
see [`ROADMAP.md`](ROADMAP.md).

## License

[Apache-2.0](LICENSE)
