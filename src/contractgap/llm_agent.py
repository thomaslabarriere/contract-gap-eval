"""The real LLM gap-analysis agent (needs a key).

Given a contract and one policy rule, it returns a structured verdict with a
verbatim evidence quote. It is graded by the same harness as the offline agent;
whether it reads clauses correctly (e.g. the C-4 IP disclaimer) is exactly what
gap-recall measures.
"""

from __future__ import annotations

import json
from typing import Any

from .llm_client import make_client
from .models import Contract, GapStatus, GapVerdict, PolicyRule, TokenUsage

_SYSTEM = (
    "Tu es un juriste qui vérifie la conformité d'un contrat à une règle de "
    "politique interne. Décide: compliant (le contrat respecte la règle), gap "
    "(écart / non conforme), ou not_applicable (la règle ne s'applique pas à ce "
    "contrat). Fonde-toi UNIQUEMENT sur le texte fourni ; cite une clause "
    "VERBATIM comme preuve (evidence). Attention aux clauses qui emploient les "
    "bons termes sans rien accorder. Appelle report_gap."
)

_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "report_gap",
        "description": "Report whether the contract complies with the rule.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["compliant", "gap", "not_applicable"]},
                "evidence": {"type": "string", "description": "Verbatim clause quote."},
                "explanation": {"type": "string"},
            },
            "required": ["status", "explanation"],
            "additionalProperties": False,
        },
    },
}


def _undecided(rule_id: str, explanation: str) -> GapVerdict:
    # An undecided call must never claim compliance -> not_applicable + note.
    return GapVerdict(rule_id=rule_id, status=GapStatus.NOT_APPLICABLE, explanation=explanation)


class LLMAgent:
    def __init__(self, model: str = "gpt-4o", provider: str = "openai") -> None:
        self.name = f"llm:{model}"
        self._model = model
        self._client = make_client(provider)

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]:
        user = (
            f"Règle {rule.rule_id} — {rule.title}\n{rule.statement}\n\n"
            f"Contrat {contract.contract_id} — {contract.title}\n"
            f"Champs: délai de paiement={contract.payment_days}, "
            f"plafond de responsabilité={contract.liability_cap}, "
            f"loi applicable={contract.governing_law or 'non précisée'}, "
            f"données personnelles={'oui' if contract.has_personal_data else 'non'}\n\n"
            f"Clauses:\n{contract.full_text()}"
        )
        try:
            completion = self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model,
                tools=[_TOOL],
                tool_choice="required",
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # noqa: BLE001 - an errored call must not claim compliance
            return _undecided(rule.rule_id, f"[erreur] {exc}"), TokenUsage()

        usage = TokenUsage(
            prompt_tokens=getattr(completion.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(completion.usage, "completion_tokens", 0) or 0,
        )
        message = completion.choices[0].message if completion.choices else None
        for call in getattr(message, "tool_calls", None) or []:
            if getattr(call, "type", None) == "function" and call.function.name == "report_gap":
                parsed = _parse(rule.rule_id, call.function.arguments)
                if parsed is not None:
                    return parsed, usage
        return _undecided(rule.rule_id, "no verdict"), usage


def _parse(rule_id: str, args_json: str) -> GapVerdict | None:
    try:
        data = json.loads(args_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get("status")
    if not isinstance(raw, str):
        return None
    try:
        status = GapStatus(raw)
    except ValueError:
        return None
    evidence = data.get("evidence")
    return GapVerdict(
        rule_id=rule_id,
        status=status,
        evidence=evidence if isinstance(evidence, str) and evidence else None,
        explanation=str(data.get("explanation", "")),
    )
