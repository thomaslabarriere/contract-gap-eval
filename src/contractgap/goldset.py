"""Ground truth per (contract, rule).

Structured rules are labelled objectively by their reference check over the
extracted fields (so labels can't drift from the contracts). Judgment rules are
hand-labelled here, because they turn on reading the clause text — including the
C-4 IP clause that names the right words but grants nothing to the client.
"""

from __future__ import annotations

from .contracts import CONTRACTS
from .models import GapStatus, GoldItem, GroundGoldItem, RuleKind
from .policy import REFERENCE_CHECKS, RULES, get_rule

# Hand-authored ground truth for JUDGMENT rules, keyed (contract_id, rule_id).
_JUDGMENT_LABELS: dict[tuple[str, str], GapStatus] = {
    # RGPD-28 (applies only when personal data is processed)
    ("C-1", "RGPD-28"): GapStatus.COMPLIANT,
    ("C-2", "RGPD-28"): GapStatus.GAP,           # personal data, no art. 28 clause
    ("C-3", "RGPD-28"): GapStatus.NOT_APPLICABLE,  # no personal data
    ("C-4", "RGPD-28"): GapStatus.COMPLIANT,
    # RESIL
    ("C-1", "RESIL"): GapStatus.COMPLIANT,
    ("C-2", "RESIL"): GapStatus.COMPLIANT,
    ("C-3", "RESIL"): GapStatus.COMPLIANT,
    ("C-4", "RESIL"): GapStatus.COMPLIANT,
    # IP
    ("C-1", "IP"): GapStatus.COMPLIANT,
    ("C-2", "IP"): GapStatus.COMPLIANT,
    ("C-3", "IP"): GapStatus.GAP,   # no IP clause at all
    ("C-4", "IP"): GapStatus.GAP,   # clause grants nothing to the client (semantic gap)
    # CONF
    ("C-1", "CONF"): GapStatus.COMPLIANT,
    ("C-2", "CONF"): GapStatus.COMPLIANT,
    ("C-3", "CONF"): GapStatus.GAP,  # no confidentiality clause
    ("C-4", "CONF"): GapStatus.COMPLIANT,
}


def build_gold_set() -> list[GoldItem]:
    items: list[GoldItem] = []
    for contract in CONTRACTS:
        for rule in RULES:
            if rule.kind is RuleKind.STRUCTURED:
                expected = REFERENCE_CHECKS[rule.rule_id](contract)
            else:
                expected = _JUDGMENT_LABELS[(contract.contract_id, rule.rule_id)]
            items.append(
                GoldItem(contract_id=contract.contract_id, rule_id=rule.rule_id, expected=expected)
            )
    return items


# Labelled examples for calibrating the evidence-relevance judge: does the
# cited clause pertain to the rule (True) or is it a real-but-irrelevant one?
GROUND_GOLD: list[GroundGoldItem] = [
    GroundGoldItem(contract_id="C-1", rule_id="RGPD-28",
                   evidence="clause de sous-traitance au sens de l'article 28 du RGPD", supports_gap=True),
    GroundGoldItem(contract_id="C-2", rule_id="PAY-60",
                   evidence="le paiement intervient à 90 jours", supports_gap=True),
    GroundGoldItem(contract_id="C-4", rule_id="IP",
                   evidence="aucune cession de propriété intellectuelle n'est consentie", supports_gap=True),
    GroundGoldItem(contract_id="C-1", rule_id="RESIL",
                   evidence="résiliation en cas de manquement d'une partie", supports_gap=True),
    GroundGoldItem(contract_id="C-2", rule_id="RGPD-28",
                   evidence="une clause de confidentialité standard est applicable", supports_gap=False),
    GroundGoldItem(contract_id="C-2", rule_id="CONF",
                   evidence="ce contrat est soumis au droit anglais", supports_gap=False),
]


def gold_status(contract_id: str, rule_id: str) -> GapStatus:
    rule = get_rule(rule_id)
    if rule.kind is RuleKind.STRUCTURED:
        from .contracts import get_contract

        return REFERENCE_CHECKS[rule_id](get_contract(contract_id))
    return _JUDGMENT_LABELS[(contract_id, rule_id)]
