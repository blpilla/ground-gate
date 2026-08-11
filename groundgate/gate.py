"""The runtime faithfulness gate: ``verify(answer, context) -> Verdict``.

Pipeline per claim:

1. Citation check — if the claim cites sources, only the cited sources may
   support it, and a citation to an unknown source fails immediately.
2. Deterministic match — verbatim containment, token-window coverage and
   number consistency (see ``matcher``). Decides most claims with zero cost.
3. Judge escalation — only AMBIGUOUS matches reach the (optional) LLM judge.
   With no judge configured the gate fails closed by default.
"""

from __future__ import annotations

from typing import Sequence

from .decompose import decompose
from .judge import Judge
from .matcher import MatchOutcome, match_claim
from .types import Claim, ClaimVerdict, Source, Verdict

ContextLike = str | Sequence[str] | Sequence[dict] | Sequence[Source]


def coerce_sources(context: ContextLike) -> list[Source]:
    """Accept a plain string, list of strings, dicts or Sources."""
    if isinstance(context, str):
        return [Source(id="1", text=context)]
    sources: list[Source] = []
    for position, item in enumerate(context, start=1):
        if isinstance(item, Source):
            sources.append(item)
        elif isinstance(item, str):
            sources.append(Source(id=str(position), text=item))
        elif isinstance(item, dict):
            sources.append(
                Source(id=str(item.get("id", position)), text=str(item["text"]))
            )
        else:
            raise TypeError(f"unsupported context item type: {type(item)!r}")
    return sources


class GroundGate:
    """Configurable gate. For one-off use, prefer the module-level ``verify``.

    Args:
        judge: optional LLM judge for ambiguous claims (see
            ``groundgate.providers``). Any object with a
            ``judge(claim, evidence) -> JudgeResult`` method works.
        require_citations: when True, every claim must carry at least one
            citation marker; uncited claims fail.
        fail_open: when True, ambiguous claims with no judge configured are
            let through instead of failing. Keep False in regulated domains.
    """

    def __init__(
        self,
        judge: Judge | None = None,
        require_citations: bool = False,
        fail_open: bool = False,
    ):
        self.judge = judge
        self.require_citations = require_citations
        self.fail_open = fail_open

    def verify(self, answer: str, context: ContextLike) -> Verdict:
        sources = coerce_sources(context)
        claims = decompose(answer)
        if not claims:
            return Verdict(
                passed=True, claims=(), reasons=("answer contains no checkable claims",)
            )

        verdicts = tuple(self._verify_claim(claim, sources) for claim in claims)
        failures = tuple(
            f"unsupported claim: {v.claim.text!r} ({v.reason})"
            for v in verdicts
            if not v.supported
        )
        return Verdict(passed=not failures, claims=verdicts, reasons=failures)

    def _verify_claim(self, claim: Claim, sources: list[Source]) -> ClaimVerdict:
        candidates = sources
        if claim.citations:
            by_id = {s.id: s for s in sources}
            unknown = [c for c in claim.citations if c not in by_id]
            if unknown:
                return ClaimVerdict(
                    claim=claim,
                    supported=False,
                    confidence=1.0,
                    reason=f"citation points to unknown source: {', '.join(unknown)}",
                    method="citation",
                )
            # A citation is a promise: the cited sources must do the supporting.
            candidates = [by_id[c] for c in claim.citations]
        elif self.require_citations:
            return ClaimVerdict(
                claim=claim,
                supported=False,
                confidence=1.0,
                reason="claim carries no citation and citations are required",
                method="citation",
            )

        match = match_claim(claim.text, candidates)

        if match.outcome is MatchOutcome.SUPPORTED:
            return ClaimVerdict(
                claim=claim,
                supported=True,
                confidence=match.score,
                reason=match.reason,
                method="deterministic",
                source_span=match.span,
            )
        if match.outcome is MatchOutcome.UNSUPPORTED:
            return ClaimVerdict(
                claim=claim,
                supported=False,
                confidence=1.0 - match.score,
                reason=match.reason,
                method="deterministic",
                source_span=match.span,
            )

        # AMBIGUOUS: escalate to the judge if we have one.
        if self.judge is not None:
            evidence = (
                match.span.text
                if match.span
                else "\n\n".join(s.text for s in candidates)
            )
            result = self.judge.judge(claim.text, evidence)
            return ClaimVerdict(
                claim=claim,
                supported=result.supported,
                confidence=result.confidence,
                reason=result.reason,
                method="judge",
                source_span=match.span,
            )

        if self.fail_open:
            return ClaimVerdict(
                claim=claim,
                supported=True,
                confidence=match.score,
                reason=f"{match.reason}; no judge configured, gate is fail-open",
                method="policy",
                source_span=match.span,
            )
        return ClaimVerdict(
            claim=claim,
            supported=False,
            confidence=1.0 - match.score,
            reason=f"{match.reason}; no judge configured, gate fails closed",
            method="policy",
            source_span=match.span,
        )


_default_gate = GroundGate()


def verify(answer: str, context: ContextLike, **gate_kwargs) -> Verdict:
    """One-line integration: ``verify(answer, context) -> Verdict``.

    Keyword arguments (``judge``, ``require_citations``, ``fail_open``) build
    a configured :class:`GroundGate` on the fly; with none, a shared
    deterministic, fail-closed gate is used.
    """
    gate = GroundGate(**gate_kwargs) if gate_kwargs else _default_gate
    return gate.verify(answer, context)
