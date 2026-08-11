"""GroundGate — runtime faithfulness gate for RAG.

One-line integration::

    from groundgate import verify

    verdict = verify(answer, context)
    if not verdict.passed:
        ...  # block, regenerate or re-retrieve
"""

__version__ = "0.1.0"

from .gate import GroundGate, verify
from .judge import Judge, JudgeResult
from .types import Claim, ClaimVerdict, Source, Span, Verdict

__all__ = [
    "__version__",
    "GroundGate",
    "verify",
    "Judge",
    "JudgeResult",
    "Claim",
    "ClaimVerdict",
    "Source",
    "Span",
    "Verdict",
]
