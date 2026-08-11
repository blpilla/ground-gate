"""Decompose an answer into atomic, checkable claims.

Deterministic by design: sentence-level splitting plus citation extraction.
An LLM-based decomposer can be added later behind the same interface, but the
v0.1 rule is "determinism where possible" — most RAG answers are already
written one fact per sentence, and a deterministic split never flickers.
"""

from __future__ import annotations

import re

from .text import content_tokens, split_sentences
from .types import Claim

# Citation markers accepted: [1], [doc-2], [policy_a], (fonte: 1), (source: 1)
_BRACKET_CITATION = re.compile(r"\[([^\[\]]{1,40}?)\]")
_PAREN_CITATION = re.compile(r"\((?:fonte|source)\s*:\s*([^)]{1,40}?)\)", re.IGNORECASE)

# Sentences that carry no verifiable fact and should not be gated.
_MIN_CONTENT_TOKENS = 2


def extract_citations(sentence: str) -> tuple[str, tuple[str, ...]]:
    """Return the sentence with citation markers removed, plus the citation ids."""
    citations: list[str] = []

    def _collect(match: re.Match[str]) -> str:
        citations.append(match.group(1).strip())
        return ""

    cleaned = _BRACKET_CITATION.sub(_collect, sentence)
    cleaned = _PAREN_CITATION.sub(_collect, cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", cleaned)).strip()
    return cleaned, tuple(citations)


def is_checkable(sentence: str) -> bool:
    """Filter out sentences that state no verifiable fact."""
    if sentence.endswith("?"):
        return False
    return len(content_tokens(sentence)) >= _MIN_CONTENT_TOKENS


def decompose(answer: str) -> list[Claim]:
    """Split an answer into atomic claims with their citation ids."""
    claims: list[Claim] = []
    for sentence in split_sentences(answer):
        text, citations = extract_citations(sentence)
        if is_checkable(text):
            claims.append(Claim(text=text, citations=citations))
    return claims
