import json
from pathlib import Path

import pytest

from groundgate import GroundGate, verify
from groundgate.judge import JudgeResult

PAIRS = json.loads(
    (Path(__file__).parent / "data" / "insurance_pairs.json").read_text("utf-8")
)["cases"]


class FakeJudge:
    """Deterministic stand-in for an LLM judge."""

    def __init__(self, supported: bool, reason: str = "fake judge"):
        self.supported = supported
        self.calls: list[tuple[str, str]] = []
        self.reason = reason

    def judge(self, claim: str, evidence: str) -> JudgeResult:
        self.calls.append((claim, evidence))
        return JudgeResult(self.supported, 0.9, self.reason)


@pytest.mark.parametrize("case", PAIRS, ids=[c["name"] for c in PAIRS])
def test_faithful_answers_pass(case):
    verdict = verify(case["faithful"], case["context"])
    assert verdict.passed, verdict.reasons
    assert verdict.status == "pass"
    assert verdict.score == 1.0


@pytest.mark.parametrize("case", PAIRS, ids=[c["name"] for c in PAIRS])
def test_unfaithful_answers_fail(case):
    verdict = verify(case["unfaithful"], case["context"])
    assert not verdict.passed
    assert verdict.status == "fail"
    assert verdict.unsupported_claims
    assert verdict.reasons


def test_structured_output_shape():
    verdict = verify(
        "A carencia e de 24 horas [1].",
        [{"id": "1", "text": "A carencia do plano e de 24 horas."}],
    )
    payload = verdict.to_dict()
    assert payload["status"] == "pass"
    (claim,) = payload["claims"]
    assert set(claim) == {
        "claim",
        "citations",
        "supported",
        "confidence",
        "reason",
        "method",
        "source_span",
    }
    assert claim["source_span"]["source_id"] == "1"


def test_citation_to_unknown_source_fails():
    verdict = verify(
        "A carencia e de 24 horas [99].",
        [{"id": "1", "text": "A carencia do plano e de 24 horas."}],
    )
    assert not verdict.passed
    assert "unknown source" in verdict.claims[0].reason


def test_require_citations_fails_uncited_claims():
    context = [{"id": "1", "text": "A carencia do plano e de 24 horas."}]
    assert verify("A carencia e de 24 horas.", context).passed
    verdict = verify("A carencia e de 24 horas.", context, require_citations=True)
    assert not verdict.passed
    assert verdict.claims[0].method == "citation"


def test_ambiguous_claim_escalates_to_judge():
    context = "O segurado deve comunicar o sinistro a seguradora em ate 30 dias corridos."
    claim = "O segurado deve comunicar o sinistro rapidamente ao corretor responsavel."

    approving = FakeJudge(supported=True)
    verdict = GroundGate(judge=approving).verify(claim, context)
    assert verdict.passed
    assert verdict.claims[0].method == "judge"
    assert approving.calls, "judge was not consulted"

    rejecting = FakeJudge(supported=False, reason="different addressee")
    verdict = GroundGate(judge=rejecting).verify(claim, context)
    assert not verdict.passed
    assert verdict.claims[0].reason == "different addressee"


def test_ambiguous_without_judge_fails_closed_by_default():
    context = "O segurado deve comunicar o sinistro a seguradora em ate 30 dias corridos."
    claim = "O segurado deve comunicar o sinistro rapidamente ao corretor responsavel."

    closed = GroundGate().verify(claim, context)
    assert not closed.passed
    assert closed.claims[0].method == "policy"

    open_gate = GroundGate(fail_open=True).verify(claim, context)
    assert open_gate.passed


def test_supported_claims_never_reach_the_judge():
    judge = FakeJudge(supported=False)
    verdict = GroundGate(judge=judge).verify(
        "A carencia e de 24 horas.", "A carencia do plano e de 24 horas."
    )
    assert verdict.passed
    assert judge.calls == []


def test_empty_answer_passes_with_note():
    verdict = verify("", "qualquer contexto")
    assert verdict.passed
    assert verdict.claims == ()
