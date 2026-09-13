"""Synthetic contracts (a supplier/commercial portfolio, invented).

Fields (payment days, liability cap, governing law) stand in for what an
extraction step would pull out; clause texts carry the judgment-rule content.
One IP clause (C-4) mentions the right words but actually GRANTS NOTHING to the
client, a semantic gap a keyword scan misses but an expert (or an LLM) catches.
No real contracts. Not legal advice.
"""

from __future__ import annotations

from .models import Clause, Contract

CONTRACTS: list[Contract] = [
    Contract(
        contract_id="C-1",
        title="Prestation SaaS, Fournisseur A",
        payment_days=45.0,
        liability_cap=500000.0,
        governing_law="français",
        has_personal_data=True,
        clauses=[
            Clause(heading="Responsabilité", text="La responsabilité du prestataire est plafonnée à 500 000 euros."),
            Clause(heading="Paiement", text="Les factures sont réglées à 45 jours."),
            Clause(heading="Loi applicable", text="Le présent contrat est régi par le droit français."),
            Clause(
                heading="Protection des données",
                text="Le prestataire agit comme sous-traitant au sens de l'article 28 du RGPD pour le traitement des données personnelles.",
            ),
            Clause(heading="Résiliation", text="En cas de manquement grave, chaque partie peut résilier le contrat."),
            Clause(heading="Propriété intellectuelle", text="Les livrables font l'objet d'une cession de propriété intellectuelle au client."),
            Clause(heading="Confidentialité", text="Les parties s'engagent à la confidentialité des informations échangées."),
        ],
    ),
    Contract(
        contract_id="C-2",
        title="Contrat de fourniture, Fournisseur B",
        payment_days=90.0,
        liability_cap=None,
        governing_law="anglais",
        has_personal_data=True,
        clauses=[
            Clause(heading="Paiement", text="Le paiement intervient à 90 jours fin de mois."),
            Clause(heading="Loi applicable", text="Ce contrat est soumis au droit anglais."),
            Clause(heading="Résiliation", text="Le contrat peut être résilié en cas de manquement."),
            Clause(heading="Propriété intellectuelle", text="Une licence d'utilisation des livrables est concédée au client."),
            Clause(heading="Confidentialité", text="Une clause de confidentialité standard est applicable."),
        ],
    ),
    Contract(
        contract_id="C-3",
        title="Contrat de conseil, Fournisseur C",
        payment_days=60.0,
        liability_cap=200000.0,
        governing_law="français",
        has_personal_data=False,
        clauses=[
            Clause(heading="Responsabilité", text="La responsabilité est limitée à 200 000 euros."),
            Clause(heading="Paiement", text="Règlement à 60 jours."),
            Clause(heading="Loi applicable", text="Le droit français est applicable."),
            Clause(heading="Résiliation", text="Résiliation possible en cas de manquement d'une partie."),
        ],
    ),
    Contract(
        contract_id="C-4",
        title="Contrat de développement, Fournisseur D",
        payment_days=None,
        liability_cap=100000.0,
        governing_law="français",
        has_personal_data=True,
        clauses=[
            Clause(heading="Responsabilité", text="Responsabilité plafonnée à 100 000 euros."),
            Clause(heading="Loi applicable", text="Le droit français régit le contrat."),
            Clause(
                heading="Données personnelles",
                text="Le prestataire, sous-traitant au sens du RGPD, protège les données personnelles traitées.",
            ),
            Clause(
                heading="Propriété intellectuelle",
                text="Le prestataire conserve l'intégralité des droits de propriété intellectuelle ; aucune cession n'est consentie au client.",
            ),
            Clause(heading="Résiliation", text="Le contrat peut être résilié en cas de manquement d'une partie."),
            Clause(heading="Confidentialité", text="Engagement de confidentialité réciproque des parties."),
        ],
    ),
]


def get_contract(contract_id: str) -> Contract:
    for contract in CONTRACTS:
        if contract.contract_id == contract_id:
            return contract
    raise KeyError(f"unknown contract {contract_id!r}")
