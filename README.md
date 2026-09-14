# contract-gap-eval

**A contract-vs-policy gap-analysis agent, with a gap-recall reliability harness for legal review.**

An AI agent that reviews contracts is only deployable in a legal department if you can state one number: **of the real gaps, how many does it miss?** A missed non-compliant clause is the false negative that gets a client sued. `contract-gap-eval` runs an agent that compares a contract to an internal policy and produces a **gap matrix**, then measures its **gap-recall** (overall and by severity), its precision, and, objectively, whether it invents clauses that aren't there.

> **Scope.** SYNTHETIC contracts and a SIMPLIFIED illustrative internal policy, not legal advice, not a real compliance product, no client data. The value is the diagnostic instrument (and how honestly it measures missed gaps), not the legal content. Plug in a real policy + contracts for real numbers.

> **On the word "agent".** The thing under test is a **one-shot classifier/verifier**, not an autonomous agent: for each (contract, rule) pair the real-model path is a single `chat.completions.create` call with one `report_gap` tool and no planning, memory, or multi-step tool loop. Where the code and this README say "agent" it is only a loose label for "the thing being evaluated"; the offline baseline and the `lax`/`hallucinator`/oracle fixtures are plain, network-free classifiers. Plug in a genuinely agentic reviewer and the same harness still applies — it only grades the verdicts returned.

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
Matrice d'écarts: Contrat de fourniture, Fournisseur B [C-2]
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

`contract-gap-eval reliability` scores the agent against a labelled gold set of **22 real gaps across 8 contracts** (56 (contract, rule) labels). The star metric is **gap-recall by severity**, a missed *critical* gap is what destroys client trust:

```
────────────────────────────────────────────────────────────────────
Fiabilité de l'agent: heuristic
────────────────────────────────────────────────────────────────────
Gap-recall: 91% (20/22 écarts détectés)   Précision: 100%
Écarts manqués: 2 (dont critiques: 0)
Fausses alertes: 0   Citations hallucinées: 0

Recall par sévérité
  critical  100%  (5/5)
  major      86%  (12/14)
  minor     100%  (3/3)

Accord global: 96% (54/56)
```

That 91% is instructive: the offline keyword baseline **misses two major gaps**, both IP clauses (C-4 and C-7) of the form *"le prestataire conserve/demeure titulaire de l'intégralité des droits de propriété intellectuelle ; aucune cession n'est consentie au client."* They name all the right words, so a keyword scan reads them as compliant; only reading the negation reveals they grant the client nothing. Every *critical* gap is caught. Run the LLM agent (`--agent llm`) and re-measure to see whether it closes the gap, exactly the question you'd ask before trusting either one in front of a General Counsel.

The **96% global agreement** (54/56) is now an honest number: the gold labels are hand-authored in `goldset.py`, independent of the reference checks the agent uses (see *Why you can trust the harness*), so the agreement measures the agent against ground truth rather than the code grading itself.

`contract-gap-eval reliability` exits non-zero only if a **critical** gap was missed → CI gate. The offline baseline misses two *major* gaps (the IP disclaimers above) but no critical, so it passes; a lax agent that misses a critical gap fails the build.

## Run against a real model (LLM)

```bash
export OPENAI_API_KEY=sk-...            # the only thing needed to go live
contract-gap-eval check       --agent llm --model gpt-4o
contract-gap-eval reliability --agent llm --model gpt-4o
```

With a key, an LLM judges each (contract, rule) pair and cites a verbatim clause; the reliability command reports its gap-recall plus inference cost and latency.

## Two guardrails that matter for legal

- **Citation hallucination (objective).** Whenever a verdict cites a clause as evidence, that quote must **actually appear in the contract** (checked by substring), an agent that invents a clause is caught with certainty, no judgment call. (Structured-rule gaps like a missing liability cap cite a field check rather than a quote; the guard applies to every verdict that does cite text, which the LLM agent is prompted to always do.)
- **Evidence relevance (judged, and the judge is calibrated).** A cited clause can be real yet irrelevant to the rule. That softer call is delegated to a judge whose own agreement with a labelled gold set is reported by `calibrate`, *who judges the judge?*

## Why you can trust the harness

**The gold set is decoupled from the code under test.** Every expected verdict in `goldset.py` (for structured *and* judgment rules) is hand-authored from reading the contracts, not computed by calling the same `REFERENCE_CHECKS` the agent uses. A gold set derived from that shared code would grade the code with the code, inflating agreement into a tautology; a dedicated test (`test_mutating_a_reference_check_breaks_the_agent_but_not_the_gold`) proves the decoupling by **live-mutating a reference check** and asserting the gold labels do not move while the agent's measured recall drops, exactly the regression the tautology would have hidden.

**The metrics are exercised by adversarial fixture agents (mutation-style testing).** `tests/` asserts a policy-following **oracle** is perfect and clean; a **lax** agent (everything compliant) is caught with gap-recall 0 and all 5 critical gaps missed; a **hallucinator** that cites absent clauses trips the citation guard on all 56 verdicts; the keyword baseline's two semantic misses (the C-4/C-7 IP disclaimers) are reported exactly; the structured reference checks match the contracts; and the relevance judge is caught when it rubber-stamps (calibrated against 12 labelled evidence items, whose quotes are themselves verbatim and pass the same citation guard the agent is held to; `calibrate` reports 83% agreement (10/12) for the static overlap judge versus 67% for a rubber stamp).

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
  goldset.py    # ground truth (hand-authored, decoupled from the code) + judge gold
  agent.py      # heuristic baseline + lax/hallucinator fixtures + oracle
  llm_agent.py  # the real LLM gap-analysis agent (needs a key)
  judge.py      # evidence-relevance judge + calibration
  llm_client.py # shared OpenAI-compatible client
  evaluate.py   # gap matrix + gap-recall / precision / citation guard
  report.py     # render the matrix and the reliability report
  pricing.py    # illustrative token pricing
  cli.py        # check | reliability | calibrate
tests/          # adversarial fixtures + gold decoupling mutation + reference checks + calibration
```

## License

MIT
