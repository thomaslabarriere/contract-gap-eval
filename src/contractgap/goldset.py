"""Ground truth per (contract, rule) — hand-labelled, independent of the code.

Every expected verdict below is authored BY HAND from reading contracts.py, for
BOTH structured and judgment rules. Nothing here calls `REFERENCE_CHECKS` (the
same reference the agent under test uses), so the gold set cannot grade the code
with the code: the agreement it measures is real, not a tautology. The C-4 and
C-7 IP clauses name the right words while granting the client nothing (a
semantic gap a keyword scan misses); those are labelled GAP here on purpose.
"""

from __future__ import annotations

from .contracts import CONTRACTS
from .models import GapStatus, GoldItem, GroundGoldItem
from .policy import RULE_IDS, RULES

_C = GapStatus.COMPLIANT
_G = GapStatus.GAP
_NA = GapStatus.NOT_APPLICABLE

# Hand-authored ground truth for EVERY (contract, rule) pair, keyed by
# contract id, in RULE_IDS order: LIAB-CAP, PAY-60, LAW-FR, RGPD-28, RESIL, IP,
# CONF. Read off contracts.py by hand — not computed from the policy checks.
_LABELS: dict[str, tuple[GapStatus, ...]] = {
    # LIAB   PAY   LAW   RGPD  RESIL IP    CONF
    "C-1": (_C,   _C,   _C,   _C,   _C,   _C,   _C),
    "C-2": (_G,   _G,   _G,   _G,   _C,   _C,   _C),
    "C-3": (_C,   _C,   _C,   _NA,  _C,   _G,   _G),
    "C-4": (_C,   _G,   _C,   _C,   _C,   _G,   _C),
    "C-5": (_G,   _G,   _G,   _G,   _C,   _G,   _G),
    "C-6": (_C,   _C,   _C,   _NA,  _C,   _C,   _C),
    "C-7": (_C,   _G,   _G,   _C,   _G,   _G,   _C),
    "C-8": (_G,   _G,   _C,   _NA,  _C,   _G,   _G),
}


def _label(contract_id: str, rule_id: str) -> GapStatus:
    return _LABELS[contract_id][RULE_IDS.index(rule_id)]


def build_gold_set() -> list[GoldItem]:
    items: list[GoldItem] = []
    for contract in CONTRACTS:
        for rule in RULES:
            items.append(
                GoldItem(
                    contract_id=contract.contract_id,
                    rule_id=rule.rule_id,
                    expected=_label(contract.contract_id, rule.rule_id),
                )
            )
    return items


def gold_status(contract_id: str, rule_id: str) -> GapStatus:
    return _label(contract_id, rule_id)


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
    GroundGoldItem(contract_id="C-5", rule_id="PAY-60",
                   evidence="le paiement est effectué à 120 jours", supports_gap=True),
    GroundGoldItem(contract_id="C-7", rule_id="LAW-FR",
                   evidence="le présent contrat est soumis au droit belge", supports_gap=True),
    GroundGoldItem(contract_id="C-7", rule_id="IP",
                   evidence="le prestataire demeure titulaire de l'ensemble des droits de propriété intellectuelle", supports_gap=True),
    GroundGoldItem(contract_id="C-3", rule_id="IP",
                   evidence="règlement à 60 jours", supports_gap=False),
    GroundGoldItem(contract_id="C-1", rule_id="CONF",
                   evidence="les parties s'engagent à la confidentialité des informations échangées", supports_gap=True),
    GroundGoldItem(contract_id="C-4", rule_id="CONF",
                   evidence="aucune cession n'est consentie au client", supports_gap=False),
]
