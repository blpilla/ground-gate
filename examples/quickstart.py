"""GroundGate quickstart: one-line verification, no LLM required.

Run from the repository root:

    python examples/quickstart.py
"""

import json

from groundgate import verify

# What your retriever returned (insurance policy snippets).
context = [
    {
        "id": "policy",
        "text": (
            "O plano Essencial cobre consultas de emergencia com carencia de "
            "24 horas. O limite anual de reembolso e de R$ 50.000."
        ),
    }
]

# What your LLM generated — note the hallucinated waiting period.
answer = (
    "A carencia para emergencias no plano Essencial e de 12 horas [policy]. "
    "O limite anual de reembolso e de R$ 50.000 [policy]."
)

verdict = verify(answer, context)

print(f"status: {verdict.status}  (score={verdict.score:.2f})")
for claim in verdict.claims:
    marker = "PASS" if claim.supported else "FAIL"
    print(f"  [{marker}] {claim.claim.text}")
    print(f"         reason: {claim.reason}")

print("\nfull structured verdict:")
print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
