import json

from groundgate.cli import main


def test_cli_verify_pass_exit_code_and_json(tmp_path, capsys):
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps([{"id": "1", "text": "A carencia do plano e de 24 horas."}]),
        encoding="utf-8",
    )
    exit_code = main(
        ["verify", "--answer", "A carencia e de 24 horas [1].", "--context", str(context)]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "pass"


def test_cli_verify_fail_exit_code(tmp_path, capsys):
    context = tmp_path / "context.txt"
    context.write_text("A carencia do plano e de 24 horas.", encoding="utf-8")
    exit_code = main(
        ["verify", "--answer", "A carencia e de 12 horas.", "--context", str(context)]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "fail"


def test_cli_accepts_inline_context(capsys):
    exit_code = main(
        [
            "verify",
            "--answer",
            "A carencia e de 24 horas.",
            "--context",
            "A carencia do plano e de 24 horas.",
        ]
    )
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
