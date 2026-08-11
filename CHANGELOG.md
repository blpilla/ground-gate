# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-07

First release: the complete runtime faithfulness gate.

### Added

- **Core verification**: answer decomposition into atomic claims, with
  citation extraction (`[1]`, `[policy]`, `(fonte: x)` / `(source: x)`).
- **Deterministic matcher**: verbatim containment, sentence-window token
  coverage, and number-consistency checking (amounts, deadlines, limits) —
  decides most claims with zero LLM cost and no flicker.
- **Citation checking**: cited sources must themselves support the claim;
  citations to unknown sources fail immediately.
- **LLM-as-judge escalation** (optional, provider-agnostic): OpenAI,
  Anthropic, AWS Bedrock and Ollama judges, each behind an optional extra;
  any object with `judge(claim, evidence) -> JudgeResult` works.
- **Fail-closed policy** for ambiguous claims with no judge configured
  (opt-out via `fail_open=True`).
- **Python SDK**: `verify(answer, context) -> Verdict`, plus configurable
  `GroundGate` (judge, `require_citations`, `fail_open`).
- **Structured output**: per-claim
  `{claim, citations, supported, confidence, reason, method, source_span}`.
- **MCP server**: zero-dependency stdio JSON-RPC server exposing the
  `verify_grounding` tool (`groundgate mcp`).
- **CLI**: `groundgate verify` with JSON output and exit code 1 on fail.
- **Test suite**: 46 tests including paired faithful/unfaithful cases from
  regulated domains (insurance/health, pt-BR).
- **Benchmark**: reproducible comparison against naive baselines
  (`benchmark/run.py`).
- **Examples**: quickstart script, notebook, production gate loop, MCP
  integration.

[0.1.0]: https://github.com/blpilla/groundgate/releases/tag/v0.1.0
