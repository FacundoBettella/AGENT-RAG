"""Script 05 — Test de ruteo + moderación del orquestador contra test_queries.json.

Corre cada consulta a través del orquestador completo (moderación ->
clasificación -> agente de dominio) y compara el intent obtenido contra
expected_intent. Los casos con expected_intent="blocked" esperan que la
moderación levante ContentBlockedError antes de clasificar.

Los casos con category="moderation" (ver test_queries.json) además declaran
expected_moderation ("allow"/"flag"/"block") y expected_risk (categorías de
riesgo esperadas, ver services/moderation_service.py) -- para esos casos se
llama también a ModerationService.check() directo, así queda verificado no
solo el intent final sino el tipo de acción/riesgo detectado (una pregunta
con expected_moderation="flag" NO debe bloquear, pero sí debe quedar
auditada en logs/moderation_events.jsonl).

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
from factory import build_moderation_service

TEST_QUERIES_PATH = Path(__file__).parent.parent / "test_queries.json"


def _check_moderation(moderation_service, case: dict) -> tuple[bool, str]:
    """Only for category="moderation" cases: verify the action (allow/flag/
    block) and detected risk categories match what the fixture declares.
    Returns (ok, detail)."""
    risks, action, _reason = moderation_service.check(case["question"])
    expected_action = case["expected_moderation"]
    expected_risks = set(case.get("expected_risk", []))
    action_ok = action.value == expected_action
    risks_ok = expected_risks <= set(risks)
    detail = f"action={action.value} risks={risks}"
    return action_ok and risks_ok, detail


def main() -> None:
    test_cases = json.loads(TEST_QUERIES_PATH.read_text(encoding="utf-8"))
    orchestrator = build_orchestrator()
    moderation_service = build_moderation_service()

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
        detail = reasoning

        if case.get("category") == "moderation":
            mod_ok, mod_detail = _check_moderation(moderation_service, case)
            ok = ok and mod_ok
            detail = f"{reasoning} | moderation: {mod_detail}"

        passed += ok
        results.append((case["id"], case.get("category", "-"), expected, actual, ok, detail))

    print(f"{'ID':<10} {'CATEGORIA':<14} {'ESPERADO':<10} {'OBTENIDO':<10} {'OK':<5} DETALLE")
    print("-" * 130)
    for case_id, category, expected, actual, ok, detail in results:
        mark = "OK" if ok else "FAIL"
        print(f"{case_id:<10} {category:<14} {expected:<10} {actual:<10} {mark:<5} {detail}")

    total = len(test_cases)
    print(f"\nAccuracy total: {passed}/{total} ({passed / total:.0%})")

    by_category: dict[str, list[bool]] = {}
    for _id, category, _exp, _act, ok, _detail in results:
        by_category.setdefault(category, []).append(ok)
    print("\nPor categoría:")
    for category, oks in by_category.items():
        print(f"  {category:<14} {sum(oks)}/{len(oks)}")


if __name__ == "__main__":
    main()
