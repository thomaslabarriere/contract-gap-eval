# contract-gap-eval

**A contract-vs-policy gap-analysis agent — with a gap-recall reliability harness for legal review.**

An AI agent that reviews contracts is only deployable in a legal department if you can state one number: **of the real gaps, how many does it miss?** A missed non-compliant clause is the false negative that gets a client sued. `contract-gap-eval` runs an agent that compares a contract to an internal policy and produces a **gap matrix**, then measures its **gap-recall** (overall and by severity), its precision, and — objectively — whether it invents clauses that aren't there.

> **Scope.** SYNTHETIC contracts and a SIMPLIFIED illustrative internal policy — not legal advice, not a real compliance product, no client data. The value is the diagnostic instrument (and how honestly it measures missed gaps), not the legal content. Plug in a real policy + contracts for real numbers.

## Quick start (no API key needed)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

contract-gap-eval check                 # gap matrix for every contract (offline)
contract-gap-eval reliability           # how many real gaps does the agent catch?
contract-gap-eval calibrate             # how reliable is the evidence judge itself?
```

## The gap matrix (the artifact)

`contract-gap-eval check --contract C-2` produces the shippable per-contract review:

```
────────────────────────────────────────────────────────────────────
Matrice d'écarts — Contrat de fourniture — Fournisseur B [C-2]
────────────────────────────────────────────────────────────────────
Écarts: 4 / 7 règles vérifiées

!! LIAB-CAP  Plafond de responsabilité (critical)
      contrôle sur champ
!! PAY-60    Délai de paiement (major)
      contrôle sur champ
!! LAW-FR    Loi applicable (major)
      contrôle sur champ
!! RGPD-28   Sous-traitance RGPD (critical)
      clause absente
OK RESIL     Résiliation pour manquement
      preuve: « Le contrat peut être résilié en cas de manquement. »
      clause détectée
OK IP        Propriété intellectuelle
      preuve: « Une licence d'utilisation des livrables est concédée au client. »
      clause détectée
OK CONF      Confidentialité
      preuve: « Une clause de confidentialité standard est applicable. »
      clause détectée
```

## The number a legal team asks for: gap-recall

`contract-gap-eval reliability` scores the agent against a labelled gold set. The star metric is **gap-recall by severity** — a missed *critical* gap is what destroys client trust:

```
────────────────────────────────────────────────────────────────────
Fiabilité de l'agent — heuristic
────────────────────────────────────────────────────────────────────
Gap-recall: 88% (7/8 écarts détectés)   Précision: 100%
Écarts manqués: 1 (dont critiques: 0)
Fausses alertes: 0   Citations hallucinées: 0

Recall par sévérité
  critical  100%  (2/2)
  major      80%  (4/5)
  minor     100%  (1/1)
```

That 88% is instructive: the offline keyword baseline **misses one major gap** — the C-4 clause *"le prestataire conserve l'intégralité des droits de propriété intellectuelle ; aucune cession n'est consentie au client."* It names all the right words, so a keyword scan reads it as compliant; only reading the negation reveals it grants the client nothing. Run the LLM agent (`--agent llm`) and re-measure to see whether it closes the gap — exactly the question you'd ask before trusting either one in front of a General Counsel.

`contract-gap-eval reliability` exits non-zero only if a **critical** gap was missed → CI gate. The offline baseline misses one *major* gap (the IP disclaimer above) but no critical, so it passes; a lax agent that misses a critical gap fails the build.

## Run the real agent (LLM)

```bash
export OPENAI_API_KEY=sk-...            # the only thing needed to go live
contract-gap-eval check       --agent llm --model gpt-4o
contract-gap-eval reliability --agent llm --model gpt-4o
```

With a key, an LLM judges each (contract, rule) pair and cites a verbatim clause; the reliability command reports its gap-recall plus inference cost and latency.

## Two guardrails that matter for legal

- **Citation hallucination (objective).** Whenever a verdict cites a clause as evidence, that quote must **actually appear in the contract** (checked by substring) — an agent that invents a clause is caught with certainty, no judgment call. (Structured-rule gaps like a missing liability cap cite a field check rather than a quote; the guard applies to every verdict that does cite text, which the LLM agent is prompted to always do.)
- **Evidence relevance (judged, and the judge is calibrated).** A cited clause can be real yet irrelevant to the rule. That softer call is delegated to a judge whose own agreement with a labelled gold set is reported by `calibrate` — *who judges the judge?*

## Why you can trust the harness (mutation proof)

`tests/` asserts a policy-following **oracle** is perfect and clean; a **lax** agent (everything compliant) is caught with gap-recall 0 and both critical gaps missed; a **hallucinator** that cites absent clauses trips the citation guard on every verdict; the keyword baseline's single semantic miss is reported exactly; the structured reference checks match the contracts; and the relevance judge is caught when it rubber-stamps.

```bash
ruff check src tests
mypy
pytest
```

## Layout

```
src/contractgap/
  models.py     # contracts (severity, gap status, gap matrix, gold, calibration)
  policy.py     # the internal policy + deterministic reference checks (structured rules)
  contracts.py  # synthetic contracts (incl. the C-4 IP semantic-gap clause)
  goldset.py    # ground truth (objective for structured, hand for judgment) + judge gold
  agent.py      # heuristic baseline + lax/hallucinator fixtures + oracle
  llm_agent.py  # the real LLM gap-analysis agent (needs a key)
  judge.py      # evidence-relevance judge + calibration
  llm_client.py # shared OpenAI-compatible client
  evaluate.py   # gap matrix + gap-recall / precision / citation guard
  report.py     # render the matrix and the reliability report
  pricing.py    # illustrative token pricing
  cli.py        # check | reliability | calibrate
tests/          # mutation-proof + reference checks + gold shape + calibration
```

## License

MIT
