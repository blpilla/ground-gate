from groundgate.judge import build_prompt, parse_judge_response


def test_parse_clean_json():
    result = parse_judge_response(
        '{"supported": true, "confidence": 0.85, "reason": "stated verbatim"}'
    )
    assert result.supported is True
    assert result.confidence == 0.85
    assert result.reason == "stated verbatim"


def test_parse_json_wrapped_in_prose():
    result = parse_judge_response(
        'Sure! Here is my analysis:\n{"supported": false, "confidence": 0.9, '
        '"reason": "context says 24, claim says 12"}\nHope that helps.'
    )
    assert result.supported is False


def test_parse_garbage_fails_closed():
    for garbage in ("", "not json", '{"unrelated": 1}', None):
        result = parse_judge_response(garbage)
        assert result.supported is False
        assert result.confidence == 0.0


def test_confidence_is_clamped():
    assert parse_judge_response('{"supported": true, "confidence": 7}').confidence == 1.0


def test_prompt_contains_claim_and_evidence():
    prompt = build_prompt("claim text", "evidence text")
    assert "claim text" in prompt and "evidence text" in prompt
