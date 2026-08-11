"""Structured types shared across the library.

The wire format is stable and documented: integrations (MCP, HTTP, CLI)
serialize these dataclasses via ``to_dict`` and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    """One retrieved context chunk the answer may cite."""

    id: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text}


@dataclass(frozen=True)
class Claim:
    """An atomic factual statement extracted from the answer."""

    text: str
    citations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "citations": list(self.citations)}


@dataclass(frozen=True)
class Span:
    """The exact slice of a source that supports (or best matches) a claim."""

    source_id: str
    start: int
    end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


@dataclass(frozen=True)
class ClaimVerdict:
    """Per-claim outcome: the unit of explainability."""

    claim: Claim
    supported: bool
    confidence: float
    reason: str
    method: str  # "deterministic" | "judge" | "citation" | "policy"
    source_span: Span | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.text,
            "citations": list(self.claim.citations),
            "supported": self.supported,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "method": self.method,
            "source_span": self.source_span.to_dict() if self.source_span else None,
        }


@dataclass(frozen=True)
class Verdict:
    """Aggregate gate decision for one answer."""

    passed: bool
    claims: tuple[ClaimVerdict, ...] = ()
    reasons: tuple[str, ...] = field(default=())

    @property
    def status(self) -> str:
        return "pass" if self.passed else "fail"

    @property
    def score(self) -> float:
        """Fraction of claims with support (1.0 when there are no claims)."""
        if not self.claims:
            return 1.0
        return sum(1 for c in self.claims if c.supported) / len(self.claims)

    @property
    def unsupported_claims(self) -> tuple[ClaimVerdict, ...]:
        return tuple(c for c in self.claims if not c.supported)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "score": round(self.score, 3),
            "reasons": list(self.reasons),
            "claims": [c.to_dict() for c in self.claims],
        }
