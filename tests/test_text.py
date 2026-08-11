from groundgate.text import content_tokens, normalize, numbers, split_sentences


def test_normalize_strips_accents_and_case():
    assert normalize("Carência  de  24 HORAS") == "carencia de 24 horas"


def test_split_sentences_handles_abbreviations():
    text = "O Dr. Silva atende na unidade central. A carencia e de 24 horas."
    assert split_sentences(text) == [
        "O Dr. Silva atende na unidade central.",
        "A carencia e de 24 horas.",
    ]


def test_content_tokens_drop_stopwords_keep_numbers():
    tokens = content_tokens("O limite anual de reembolso é de R$ 50.000")
    assert "de" not in tokens
    assert "limite" in tokens
    assert "50" in tokens


def test_numbers_canonicalization():
    assert numbers("R$ 50.000") == {"50000"}
    assert numbers("R$ 50.000,00") == {"50000"}
    assert numbers("R$ 50,000.00") == {"50000"}
    assert numbers("carencia de 24 horas e juros de 1,5%") == {"24", "1.5"}
    assert numbers("sem numeros aqui") == set()
