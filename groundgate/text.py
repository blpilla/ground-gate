"""Text utilities: normalization, sentence splitting and tokenization.

Everything here is deterministic and dependency-free. Portuguese and English
are both supported because the anchor use case (health/insurance RAG in
Brazil) mixes the two.
"""

from __future__ import annotations

import re
import unicodedata

# Small bilingual stopword list (accent-stripped, lowercase). Deliberately
# minimal: it only needs to remove glue words so token-overlap scores reflect
# content, not article/preposition noise.
STOPWORDS = frozenset(
    """
    a o os as um uma uns umas de do da dos das em no na nos nas por pelo pela
    pelos pelas para com sem sob sobre entre ate apos e ou mas que se nao sim
    ja mais menos muito pouco tambem so ao aos as e eh sao ser sera foi era
    estar esta estao estava tem tinha ha havia seu sua seus suas dele dela
    deles delas este esta isto esse essa isso aquele aquela aquilo qual quais
    quando onde como quem cujo cuja
    the an is are was were be been being of to in on at by for with and or
    but if then than that this these those it its as from has have had do
    does did not no yes there their his her him she he they them we you i
    """.split()
)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ü0-9\"'\(\[])")
_ABBREVIATIONS = (
    "dr.", "dra.", "sr.", "sra.", "srta.", "prof.", "art.", "inc.", "ltda.",
    "no.", "nº.", "p.", "ex.", "etc.", "vs.", "mr.", "mrs.", "ms.", "st.",
)
_TOKEN = re.compile(r"[a-z0-9$%]+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize(text: str) -> str:
    """Lowercase, accent-strip and collapse whitespace."""
    return re.sub(r"\s+", " ", strip_accents(text).lower()).strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, tolerant of common abbreviations."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    raw = _SENTENCE_END.split(text)
    sentences: list[str] = []
    for part in raw:
        part = part.strip()
        if not part:
            continue
        # Re-join splits caused by abbreviations ("Dr. Silva" etc.).
        if sentences and sentences[-1].lower().endswith(_ABBREVIATIONS):
            sentences[-1] = f"{sentences[-1]} {part}"
        else:
            sentences.append(part)
    return sentences


def content_tokens(text: str) -> list[str]:
    """Normalized tokens with stopwords removed. Numbers are kept."""
    return [t for t in _TOKEN.findall(normalize(text)) if t not in STOPWORDS]


def _canonical_number(literal: str) -> str:
    """Canonicalize a numeric literal across pt-BR/en formatting.

    "50.000", "50,000" and "50.000,00" all become "50000"; "1.5" stays "1.5".
    """
    if "." in literal and "," in literal:
        last = max(literal.rfind("."), literal.rfind(","))
        int_part = re.sub(r"[.,]", "", literal[:last])
        decimal = literal[last + 1 :]
    elif "." in literal or "," in literal:
        sep = "." if "." in literal else ","
        head, *rest = literal.split(sep)
        if rest and all(len(group) == 3 for group in rest):
            int_part, decimal = head + "".join(rest), ""
        else:
            int_part, decimal = head + "".join(rest[:-1]), rest[-1]
    else:
        int_part, decimal = literal, ""
    int_part = int_part.lstrip("0") or "0"
    decimal = decimal.rstrip("0")
    return f"{int_part}.{decimal}" if decimal else int_part


def numbers(text: str) -> set[str]:
    """Canonicalized numeric literals found in the text.

    Formatting differences ("50.000,00" vs "50,000" vs "50000") never cause
    false mismatches; genuinely different values always do.
    """
    return {_canonical_number(match) for match in _NUMBER.findall(text)}
