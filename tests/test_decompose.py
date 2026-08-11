from groundgate.decompose import decompose, extract_citations


def test_decompose_splits_into_atomic_claims():
    answer = (
        "A carencia e de 24 horas [1]. O limite anual e de R$ 50.000 [2]. "
        "Posso ajudar com algo mais?"
    )
    claims = decompose(answer)
    assert [c.text for c in claims] == [
        "A carencia e de 24 horas.",
        "O limite anual e de R$ 50.000.",
    ]
    assert claims[0].citations == ("1",)
    assert claims[1].citations == ("2",)


def test_extract_citations_supports_multiple_formats():
    text, citations = extract_citations(
        "A franquia e de R$ 2.500 [doc-1] (fonte: apolice)."
    )
    assert citations == ("doc-1", "apolice")
    assert "[" not in text and "fonte" not in text


def test_uncited_sentences_have_no_citations():
    (claim,) = decompose("A carencia e de 24 horas.")
    assert claim.citations == ()
