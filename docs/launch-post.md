# Your RAG cites its sources. Do the citations hold?

*Launch post — GroundGate v0.1*

## The failure mode nobody's gate catches

Production RAG systems hallucinate even when retrieval works. The expensive
version isn't the answer with no sources — reviewers catch that. It's the
answer that **looks** grounded: fluent, confident, citation attached — where
the cited passage doesn't actually say what the answer claims.

In an insurance chatbot, that looks like this:

> **Context (retrieved, correct):** "O plano Essencial cobre consultas de
> emergência com carência de **24 horas**."
>
> **Answer (delivered):** "A carência para emergências é de **12 horas**
> [policy]."

Everything about that answer scores well on aggregate similarity: same
entities, same vocabulary, valid citation id. One number is wrong. In health,
insurance, legal or finance, one wrong number is the whole incident report.

## Why existing tools don't stop it

RAGAS, TruLens and DeepEval measure faithfulness **offline** — in CI, on
eval sets, after the fact. They tell you your pipeline hallucinates 4% of
the time; they don't stop hallucination #412 from reaching a customer at
2pm on a Tuesday. What's missing is a **gate in the request path**.

And the naive runtime gate — an aggregate similarity score over the whole
answer — fails precisely on the dangerous cases. Our benchmark makes this
concrete: on 24 paired faithful/unfaithful answers from regulated domains,
whole-answer token overlap catches only **33%** of unfaithful answers,
because an answer that hallucinates one number still overlaps the context
almost everywhere ([full results](../benchmark/RESULTS.md)).

## What GroundGate does instead

GroundGate verifies **claim by claim**:

1. **Decompose** the answer into atomic claims; extract citation markers.
2. **Check citations**: a citation is a promise — the *cited* source must
   support the claim, and citing an unknown source fails instantly.
3. **Match deterministically**: verbatim containment, token coverage inside
   a sliding source window, and number consistency. A claim whose numbers
   don't exist in the source is unsupported, full stop. This decides most
   claims in microseconds, with zero LLM cost and zero flicker.
4. **Escalate only the ambiguous** (partial-overlap paraphrases) to an
   optional LLM-as-judge — OpenAI, Anthropic, Bedrock, or fully local via
   Ollama. No judge configured? The gate **fails closed**.

The verdict is structured and explainable — per claim:

```json
{
  "claim": "A carencia para emergencias e de 12 horas.",
  "supported": false,
  "reason": "numbers not found in source: 12",
  "method": "deterministic",
  "source_span": {"source_id": "policy", "start": 0, "end": 74, "text": "..."}
}
```

Your app decides what `fail` means: block, regenerate, re-retrieve, or route
to a human.

## The numbers

Seed benchmark, 12 paired cases (insurance, health, legal — pt-BR), positive
class = unfaithful answer:

| system                    | precision | recall | F1   | ms/answer |
|---------------------------|-----------|--------|------|-----------|
| no gate (`always_pass`)   | 0.00      | 0.00   | 0.00 | ~0        |
| aggregate overlap ≥ 0.7   | 1.00      | 0.33   | 0.50 | 0.08      |
| **GroundGate** (no judge) | **1.00**  | **1.00** | **1.00** | 0.35 |

Honest caveats: curated pairs, small N, answer-level labels. The point is
not "we solved faithfulness" — it's that claim-level + number-aware checking
catches the production failure shape that aggregate scores structurally
cannot. The benchmark is reproducible (`python benchmark/run.py`) and we
want your harder cases.

## Integration is one line

```python
from groundgate import verify

verdict = verify(answer, context)
if not verdict.passed:
    ...  # block / regenerate / re-retrieve
```

Or plug it into any agent as an MCP tool — GroundGate ships a
zero-dependency MCP server:

```json
{"mcpServers": {"groundgate": {"command": "groundgate", "args": ["mcp"]}}}
```

Zero runtime dependencies. Provider-agnostic. Self-hostable — the
deterministic core never makes a network call, so your regulated-domain data
never leaves your stack.

## Get it

- `pip install groundgate`
- GitHub: <https://github.com/blpilla/groundgate>
- Examples: quickstart script & notebook, production gate loop, MCP config.

If your RAG runs in a regulated domain and hallucinated citations keep you
up at night — that's exactly who this is for. Open an issue with your
failure cases.
