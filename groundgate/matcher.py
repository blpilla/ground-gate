"""Deterministic support matching: does a source span contain the claim?

This is the cheap, flicker-free first pass. It answers three questions
without any LLM call:

1. Is the claim literally (or near-literally) contained in a source?
2. Do the claim's content tokens appear together in one source window?
3. Do the claim's numbers exist in that source? (Numbers are where regulated
   -domain hallucinations hurt most: limits, deadlines, coverage amounts.)

Outcome is one of: SUPPORTED, UNSUPPORTED, or AMBIGUOUS — the last one is the
only case escalated to an LLM judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .text import content_tokens, normalize, numbers, split_sentences
from .types import Source, Span

SUPPORT_THRESHOLD = 0.7
UNSUPPORTED_THRESHOLD = 0.4
_WINDOW_SENTENCES = 3


class MatchOutcome(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class MatchResult:
    outcome: MatchOutcome
    score: float
    span: Span | None
    reason: str


def _sentence_offsets(source: Source) -> list[tuple[int, int, str]]:
    """(start, end, sentence) triples located inside the original text."""
    offsets: list[tuple[int, int, str]] = []
    cursor = 0
    for sentence in split_sentences(source.text):
        start = source.text.find(sentence, cursor)
        if start < 0:  # normalization changed whitespace; fall back to search
            start = source.text.find(sentence.split()[0], cursor)
            start = max(start, cursor)
        end = start + len(sentence)
        offsets.append((start, end, sentence))
        cursor = end
    return offsets


def _best_window(claim_tokens: set[str], source: Source) -> tuple[float, Span | None]:
    """Best token-coverage window of up to _WINDOW_SENTENCES sentences."""
    sentences = _sentence_offsets(source)
    if not sentences or not claim_tokens:
        return 0.0, None
    best_score, best_span = 0.0, None
    for i in range(len(sentences)):
        window_tokens: set[str] = set()
        for j in range(i, min(i + _WINDOW_SENTENCES, len(sentences))):
            window_tokens.update(content_tokens(sentences[j][2]))
            score = len(claim_tokens & window_tokens) / len(claim_tokens)
            if score > best_score:
                start = sentences[i][0]
                end = sentences[j][1]
                best_score = score
                best_span = Span(
                    source_id=source.id,
                    start=start,
                    end=end,
                    text=source.text[start:end],
                )
            if score == 1.0:
                return best_score, best_span
    return best_score, best_span


def match_claim(claim_text: str, sources: list[Source]) -> MatchResult:
    """Deterministically check one claim against the given sources."""
    claim_tokens = set(content_tokens(claim_text))
    if not claim_tokens:
        return MatchResult(
            MatchOutcome.AMBIGUOUS, 0.0, None, "claim has no content tokens"
        )

    normalized_claim = normalize(claim_text)
    best = MatchResult(MatchOutcome.UNSUPPORTED, 0.0, None, "no matching source span")

    for source in sources:
        # Fast path: literal containment of the whole claim.
        normalized_source = normalize(source.text)
        idx = normalized_source.find(normalized_claim)
        if idx >= 0:
            span = _approximate_span(source, claim_text)
            return MatchResult(
                MatchOutcome.SUPPORTED, 1.0, span, "claim is verbatim in source"
            )

        score, span = _best_window(claim_tokens, source)

        # Numbers are non-negotiable: a claim whose numbers are absent from
        # the source is treated as contradicted regardless of token overlap.
        claim_numbers = numbers(claim_text)
        if claim_numbers and not claim_numbers <= numbers(source.text):
            missing = sorted(claim_numbers - numbers(source.text))
            if score > best.score:
                best = MatchResult(
                    MatchOutcome.UNSUPPORTED,
                    min(score, UNSUPPORTED_THRESHOLD - 0.01),
                    span,
                    f"numbers not found in source: {', '.join(missing)}",
                )
            continue

        if score > best.score:
            if score >= SUPPORT_THRESHOLD:
                outcome, reason = (
                    MatchOutcome.SUPPORTED,
                    f"token coverage {score:.2f} within one source window",
                )
            elif score < UNSUPPORTED_THRESHOLD:
                outcome, reason = (
                    MatchOutcome.UNSUPPORTED,
                    f"token coverage {score:.2f} below threshold",
                )
            else:
                outcome, reason = (
                    MatchOutcome.AMBIGUOUS,
                    f"token coverage {score:.2f} is inconclusive",
                )
            best = MatchResult(outcome, score, span, reason)

    return best


def _approximate_span(source: Source, claim_text: str) -> Span:
    """Locate a verbatim claim inside the original (non-normalized) text."""
    idx = normalize(source.text).find(normalize(claim_text))
    # Normalized offsets approximate original offsets closely enough for
    # display purposes when whitespace was already collapsed; clamp to range.
    start = max(0, min(idx, len(source.text) - 1))
    end = min(start + len(claim_text), len(source.text))
    return Span(source_id=source.id, start=start, end=end, text=source.text[start:end])
