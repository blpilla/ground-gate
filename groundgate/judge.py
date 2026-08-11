"""LLM-as-judge protocol, used only where determinism can't decide.

The gate escalates to a judge exclusively for AMBIGUOUS matches (paraphrases,
implicit statements). Any object with a ``judge(claim, evidence)`` method
works; providers ship in ``groundgate.providers``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class JudgeResult:
    supported: bool
    confidence: float
    reason: str


@runtime_checkable
class Judge(Protocol):
    def judge(self, claim: str, evidence: str) -> JudgeResult:
        """Decide whether the evidence supports the claim."""
        ...


PROMPT_TEMPLATE = """\
You are a strict fact-verification judge for a retrieval-augmented system.

Decide whether the EVIDENCE fully supports the CLAIM. "Supports" means a
careful reader would conclude the claim is stated by or directly entailed by
the evidence. Partial support, related-but-different facts, or missing
qualifiers count as NOT supported. Do not use outside knowledge.

CLAIM:
{claim}

EVIDENCE:
{evidence}

Answer with ONLY a JSON object, no prose:
{{"supported": true|false, "confidence": <0.0-1.0>, "reason": "<one short sentence>"}}
"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def build_prompt(claim: str, evidence: str) -> str:
    return PROMPT_TEMPLATE.format(claim=claim, evidence=evidence)


def parse_judge_response(raw: str) -> JudgeResult:
    """Parse a judge model reply, failing closed on garbage output."""
    match = _JSON_BLOCK.search(raw or "")
    if not match:
        return JudgeResult(False, 0.0, "judge returned unparseable output")
    try:
        data = json.loads(match.group(0))
        return JudgeResult(
            supported=bool(data["supported"]),
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            reason=str(data.get("reason", "no reason given")),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JudgeResult(False, 0.0, "judge returned unparseable output")
