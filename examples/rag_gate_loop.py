"""Runtime gate pattern: block / regenerate / re-retrieve before answering.

This is the loop GroundGate was built for. The fake retriever and generator
below stand in for your real RAG stack; the gate logic in `answer_with_gate`
is exactly what you would ship.

Run from the repository root:

    python examples/rag_gate_loop.py

To use an LLM judge for ambiguous claims, plug one in:

    from groundgate.providers import AnthropicJudge   # or OpenAIJudge, OllamaJudge
    gate = GroundGate(judge=AnthropicJudge())
"""

from groundgate import GroundGate, Verdict

MAX_ATTEMPTS = 2

KNOWLEDGE_BASE = {
    "carencia": (
        "O plano Essencial cobre consultas de emergencia com carencia de 24 "
        "horas apos a assinatura."
    ),
    "reembolso": (
        "O reembolso de consultas fora da rede e de ate R$ 300 por consulta, "
        "pago em 15 dias uteis."
    ),
}


def retrieve(query: str, exclude: set[str] = frozenset()) -> list[dict]:
    """Your retriever. `exclude` simulates re-retrieval with different chunks."""
    return [
        {"id": key, "text": text}
        for key, text in KNOWLEDGE_BASE.items()
        if key not in exclude
    ]


def generate(query: str, context: list[dict], attempt: int) -> str:
    """Your LLM call. First attempt hallucinates the reimbursement limit."""
    if attempt == 0:
        return (
            "O reembolso de consultas fora da rede e de ate R$ 800 por "
            "consulta [reembolso]."
        )
    return (
        "O reembolso de consultas fora da rede e de ate R$ 300 por consulta, "
        "pago em 15 dias uteis [reembolso]."
    )


def answer_with_gate(query: str) -> tuple[str | None, Verdict]:
    """The production pattern: verify before the user ever sees the answer."""
    gate = GroundGate(require_citations=True)
    context = retrieve(query)
    verdict = None
    for attempt in range(MAX_ATTEMPTS + 1):
        answer = generate(query, context, attempt)
        verdict = gate.verify(answer, context)
        if verdict.passed:
            return answer, verdict
        print(f"attempt {attempt}: gate FAILED — {'; '.join(verdict.reasons)}")
        # Your recovery strategy: regenerate, re-retrieve, or both.
    return None, verdict


if __name__ == "__main__":
    query = "Qual o limite de reembolso de consultas fora da rede?"
    answer, verdict = answer_with_gate(query)
    if answer is None:
        print("gate blocked the answer; escalate to a human or say 'nao sei'.")
    else:
        print(f"\ndelivered answer (score={verdict.score:.2f}):\n{answer}")
