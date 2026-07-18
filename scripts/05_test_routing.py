"""Script 05 — Test de ruteo del orquestador contra test_queries.json.

Corre cada consulta a través del orquestador completo (moderación ->
clasificación -> agente de dominio) y compara el intent obtenido contra
expected_intent. Los casos con expected_intent="blocked" esperan que la
moderación levante ContentBlockedError antes de clasificar.

Uso:
    python scripts/05_test_routing.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.orchestrator import build_orchestrator
from domain.exceptions import ContentBlockedError

TEST_QUERIES_PATH = Path(__file__).parent.parent / "test_queries.json"


def main() -> None:
    test_cases = json.loads(TEST_QUERIES_PATH.read_text(encoding="utf-8"))
    orchestrator = build_orchestrator()

    passed = 0
    results = []

    for case in test_cases:
        question = case["question"]
        expected = case["expected_intent"]

        try:
            result = orchestrator.handle(question)
            actual = result.intent
            reasoning = result.reasoning
        except ContentBlockedError as e:
            actual = "blocked"
            reasoning = e.reason

        ok = actual == expected
        passed += ok
        results.append((case["id"], expected, actual, ok, reasoning))

    print(f"{'ID':<10} {'ESPERADO':<10} {'OBTENIDO':<10} {'OK':<5} REASONING")
    print("-" * 110)
    for case_id, expected, actual, ok, reasoning in results:
        mark = "OK" if ok else "FAIL"
        print(f"{case_id:<10} {expected:<10} {actual:<10} {mark:<5} {reasoning}")

    total = len(test_cases)
    print(f"\nAccuracy de ruteo: {passed}/{total} ({passed / total:.0%})")


if __name__ == "__main__":
    main()
