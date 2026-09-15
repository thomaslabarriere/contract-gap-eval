# Design decisions

The code here was produced by orchestrating coding agents. This document is the part that was not: the choices, the alternatives I rejected, and the reasons behind them. If you are evaluating this repo, this is where the judgment lives, not in the fact that the tests pass.

Each entry: what I chose, what I rejected, why. The last section is what this harness deliberately does **not** prove, stated so no reader assumes more than the evidence supports.

---

## 1. The star metric is gap-recall by severity, not overall accuracy

**Chosen.** The reliability report is built around **gap-recall split by severity** (`evaluate_reliability` in `src/contractgap/evaluate.py`, `recall_by_severity`). A legal team's real question is not "how accurate is the agent" but "of the real gaps, how many did it miss, and were any of them critical?"

**Rejected:** a single accuracy or F1 number over all (contract, rule) pairs.

**Why.** In contract review the costly failure is asymmetric: a missed non-compliant clause is the false negative that gets a client sued, and a missed *critical* gap is categorically worse than a missed *minor* one. A blended accuracy score lets a high overall number hide a missed critical gap behind a mass of correctly-cleared rules. Splitting recall by severity keeps the dangerous miss visible on its own line.

## 2. The CI gate fires only on a missed critical gap

**Chosen.** `contract-gap-eval reliability` exits non-zero only when a **critical** gap was missed (`critical_missed` in `evaluate.py`). The offline keyword baseline misses two *major* IP gaps but no critical, so it passes; a lax agent that misses a critical gap fails the build.

**Rejected:** gating on overall recall, or on any missed gap regardless of severity.

**Why.** The gate encodes the same asymmetry as decision 1 as an executable policy. A blanket "any miss fails" gate would either be set so loose it is meaningless or so tight that an honest agent with a couple of minor misses can never ship. Tying the build to the failure that actually destroys client trust makes the gate a real deployment decision, not a vanity threshold.

## 3. The gold set is hand-authored and decoupled from the code under test

**Chosen.** Every expected verdict in `goldset.py` is authored by hand from reading the contracts, independent of the `REFERENCE_CHECKS` the agent uses. A dedicated test (`test_mutating_a_reference_check_breaks_the_agent_but_not_the_gold`) live-mutates a reference check and asserts the gold labels do not move while the agent's measured recall drops.

**Rejected:** deriving the gold labels by calling the same reference checks the agent relies on.

**Why.** A gold set computed from the code under test grades the code with the code: agreement becomes a tautology that inflates to near-100% and hides exactly the regression you built the harness to catch. Decoupling makes the 96% global agreement an honest measurement of the agent against ground truth, and the mutation test proves the decoupling holds rather than just asserting it.

## 4. Citation hallucination is an objective substring check, not a judgment call

**Chosen.** Whenever a verdict cites a clause as evidence, that quote must actually appear in the contract, verified by a normalized substring test (`citation_hallucinated` in `evaluate.py`: `_norm(evidence) not in _norm(full_text)`). An agent that invents a clause is caught with certainty.

**Rejected:** asking a model to judge whether the cited evidence is genuine.

**Why.** A fabricated clause is the failure mode that most easily fools a human reviewer skimming a plausible report, so the guard against it must not itself be fallible. Whether a quote is physically present in the contract is a fact, not an opinion, so this guard carries no judgment risk. The softer question (is a real quote actually relevant to the rule) is a separate, judged concern, deliberately not conflated with this one.

## 5. The relevance judge is itself calibrated against a labelled gold set

**Chosen.** A cited clause can be real yet irrelevant. That softer call is delegated to a judge whose own agreement with a labelled gold set is reported by `contract-gap-eval calibrate` (`judge.py`, `test_calibrate.py`), which shows 83% agreement (10/12) for the static overlap judge versus 67% for a rubber stamp.

**Rejected:** trusting the judge silently, with no measurement of the judge's own reliability.

**Why.** A harness that grades an agent with an unmeasured judge just moves the trust problem one level up: who judges the judge? Reporting the judge's calibration, including the rubber-stamp baseline that a useless judge would score, makes the judge's own error rate a visible number rather than a hidden assumption. The evidence-gold quotes are themselves verbatim and pass the same citation guard the agent is held to.

## 6. Offline by default, real model behind one flag

**Chosen.** `check`, `reliability`, and `calibrate` all run offline against a heuristic baseline with no API key. The real LLM agent is one flag away (`--agent llm`, needing only `OPENAI_API_KEY`), routed through a shared `llm_client.py` seam so the LLM and offline paths present the same interface to the harness.

**Rejected:** requiring a live model to run or evaluate anything.

**Why.** An evaluation harness that only works with a paid key and a network is not reproducible: a reviewer cannot run it, and CI cannot gate on it deterministically. Making the offline baseline first-class means the tests, the mutation proofs, and the CI gate are all deterministic and free, while the same harness grades a real model unchanged the moment a key is present.

## 7. Metrics are exercised by adversarial fixture agents (mutation-style testing)

**Chosen.** The tests assert a policy-following **oracle** is perfect and clean; a **lax** agent (everything compliant) is caught with gap-recall 0 and all critical gaps missed; a **hallucinator** that cites absent clauses trips the citation guard on all 56 verdicts; and the keyword baseline's two known semantic misses (the C-4/C-7 IP disclaimers) are reported exactly.

**Rejected:** testing only the happy path (the oracle passes) and asserting the metric numbers on the real agent alone.

**Why.** A metric that only ever sees good input is untested against the failure it exists to catch. Feeding each metric an agent deliberately built to break it (lie compliant, fabricate citations, miss semantic gaps) proves the metric fires when it should, not just that it stays quiet when everything is fine. This is the same discipline as a mutation test: break the input on purpose and assert the instrument notices.

## 8. "Agent" is a disclosed loose label, not a claim of autonomy

**Chosen.** The thing under test is a **one-shot classifier/verifier**: for each (contract, rule) pair the real-model path is a single tool-call with one `report_gap` tool, no planning, memory, or multi-step loop. The README states this plainly and says the same harness applies to a genuinely agentic reviewer, since it only grades the returned verdicts.

**Rejected:** dressing the one-shot classifier up as an autonomous agent, or building a multi-step loop the task does not need.

**Why.** Overselling "agent" would be exactly the kind of confident-but-wrong claim this repo is built to detect in others. The evaluation is verdict-level, so autonomy is orthogonal to what the harness measures; being honest about the classifier keeps the reader's trust and keeps the boundary of the claim precise.

---

## What this harness does NOT prove

- **The numbers are on synthetic content:** 8 synthetic contracts, a simplified illustrative internal policy, 22 gaps across 56 (contract, rule) labels. No statistical power; they exercise the failure taxonomy, they are not a benchmark.
- **The internal policy is a teaching model, not a real compliance ruleset.** The reference checks behave correctly over the synthetic contracts; they are not a General Counsel's policy. Plug in a real policy and real contracts for real numbers.
- **The thing under test is a one-shot classifier, not an autonomous agent** (decision 8). The harness grades verdicts, so it applies to a real agent unchanged, but it does not itself demonstrate agentic behaviour.
- **The relevance judge is calibrated on 12 labelled evidence items** (decision 5): enough to show it beats a rubber stamp, not enough to certify it. It reports its own agreement rather than claiming to be right.
- **No legal authority and no client data.** This is a diagnostic instrument for how honestly an agent's missed gaps are measured, not legal advice and not a compliance product.

The value is the instrument, the gap-recall-by-severity metric, the decoupled gold set, and the choices above, not the synthetic content. If you are evaluating this: pick any decision and ask me why, and where it would still lie to me.
