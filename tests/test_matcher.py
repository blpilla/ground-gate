from groundgate.matcher import MatchOutcome, match_claim
from groundgate.types import Source

POLICY = Source(
    id="1",
    text=(
        "O plano Essencial cobre consultas de emergencia com carencia de 24 "
        "horas. O limite anual de reembolso e de R$ 50.000. O segurado deve "
        "comunicar o sinistro a seguradora em ate 30 dias corridos."
    ),
)


def test_verbatim_claim_is_supported_with_span():
    result = match_claim("O limite anual de reembolso e de R$ 50.000", [POLICY])
    assert result.outcome is MatchOutcome.SUPPORTED
    assert result.score == 1.0
    assert result.span is not None and result.span.source_id == "1"


def test_paraphrase_with_high_token_coverage_is_supported():
    result = match_claim(
        "A carencia para consultas de emergencia no plano Essencial e de 24 horas",
        [POLICY],
    )
    assert result.outcome is MatchOutcome.SUPPORTED
    assert result.span is not None


def test_number_mismatch_is_unsupported_even_with_high_overlap():
    result = match_claim(
        "A carencia para consultas de emergencia no plano Essencial e de 12 horas",
        [POLICY],
    )
    assert result.outcome is MatchOutcome.UNSUPPORTED
    assert "12" in result.reason


def test_unrelated_claim_is_unsupported():
    result = match_claim(
        "A apolice cobre transplantes internacionais com acompanhante e traslado",
        [POLICY],
    )
    assert result.outcome is MatchOutcome.UNSUPPORTED


def test_partial_overlap_is_ambiguous():
    result = match_claim(
        "O segurado deve comunicar o sinistro rapidamente ao corretor responsavel",
        [POLICY],
    )
    assert result.outcome is MatchOutcome.AMBIGUOUS
