"""The internal legal policy: rules a contract is checked against.

Structured rules carry a deterministic reference check over extracted fields
(objective ground truth for the gold set). Judgment rules turn on the clause
text and are labelled by hand in goldset.py.

SIMPLIFIED illustrations loosely inspired by common enterprise contracting
standards — NOT the actual regulation or legal advice.
"""

from __future__ import annotations

from collections.abc import Callable

from .models import Contract, GapStatus, PolicyRule, RuleKind, Severity

MAX_PAYMENT_DAYS = 60.0

RULES: list[PolicyRule] = [
    PolicyRule(
        rule_id="LIAB-CAP",
        title="Plafond de responsabilité",
        statement=(
            "Le contrat doit plafonner la responsabilité du prestataire. "
            "Un plafond doit être stipulé ; son absence (ou une responsabilité "
            "illimitée) est un écart critique."
        ),
        kind=RuleKind.STRUCTURED,
        severity=Severity.CRITICAL,
    ),
    PolicyRule(
        rule_id="PAY-60",
        title="Délai de paiement",
        statement=(
            "Le délai de paiement ne doit pas dépasser 60 jours. Un délai "
            "supérieur, ou l'absence de délai stipulé, est un écart."
        ),
        kind=RuleKind.STRUCTURED,
        severity=Severity.MAJOR,
    ),
    PolicyRule(
        rule_id="LAW-FR",
        title="Loi applicable",
        statement=(
            "Le contrat doit être régi par le droit français. Une autre loi "
            "applicable, ou l'absence de clause, est un écart."
        ),
        kind=RuleKind.STRUCTURED,
        severity=Severity.MAJOR,
    ),
    PolicyRule(
        rule_id="RGPD-28",
        title="Sous-traitance RGPD",
        statement=(
            "Si le contrat implique un traitement de données personnelles, il "
            "doit comporter une clause de sous-traitance conforme à l'article 28 "
            "du RGPD. Sinon la règle est non applicable."
        ),
        kind=RuleKind.JUDGMENT,
        severity=Severity.CRITICAL,
    ),
    PolicyRule(
        rule_id="RESIL",
        title="Résiliation pour manquement",
        statement=(
            "Le contrat doit prévoir une clause de résiliation en cas de "
            "manquement d'une partie."
        ),
        kind=RuleKind.JUDGMENT,
        severity=Severity.MAJOR,
    ),
    PolicyRule(
        rule_id="IP",
        title="Propriété intellectuelle",
        statement=(
            "Le contrat doit définir le régime de propriété intellectuelle "
            "(cession ou licence) des livrables."
        ),
        kind=RuleKind.JUDGMENT,
        severity=Severity.MAJOR,
    ),
    PolicyRule(
        rule_id="CONF",
        title="Confidentialité",
        statement="Le contrat doit comporter une clause de confidentialité.",
        kind=RuleKind.JUDGMENT,
        severity=Severity.MINOR,
    ),
]


def get_rule(rule_id: str) -> PolicyRule:
    for rule in RULES:
        if rule.rule_id == rule_id:
            return rule
    raise KeyError(f"unknown rule {rule_id!r}")


# --- Deterministic reference checks for STRUCTURED rules ---------------------

def _check_liability_cap(contract: Contract) -> GapStatus:
    return GapStatus.COMPLIANT if contract.liability_cap is not None else GapStatus.GAP


def _check_payment(contract: Contract) -> GapStatus:
    if contract.payment_days is None:
        return GapStatus.GAP
    return GapStatus.COMPLIANT if contract.payment_days <= MAX_PAYMENT_DAYS else GapStatus.GAP


def _check_law(contract: Contract) -> GapStatus:
    return GapStatus.COMPLIANT if contract.governing_law == "français" else GapStatus.GAP


REFERENCE_CHECKS: dict[str, Callable[[Contract], GapStatus]] = {
    "LIAB-CAP": _check_liability_cap,
    "PAY-60": _check_payment,
    "LAW-FR": _check_law,
}
