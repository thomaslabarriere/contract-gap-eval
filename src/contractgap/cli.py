"""contract-gap-eval CLI.

  contract-gap-eval check       [--agent heuristic|llm] [--contract C-2]
  contract-gap-eval reliability [--agent heuristic|llm]
  contract-gap-eval calibrate   [--judge static]

Offline by default (heuristic agent + static judge). `--agent llm` runs the real
gap-analysis agent and needs OPENAI_API_KEY (or OPENROUTER_API_KEY +
--provider openrouter) -- the only thing required to run it for real.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .agent import Agent, HeuristicAgent
from .contracts import CONTRACTS, get_contract
from .evaluate import analyze_contract, evaluate_reliability
from .goldset import GROUND_GOLD, build_gold_set
from .judge import StaticRelevanceJudge, calibrate_judge
from .report import render_contract_report, render_reliability_report


def _build_agent(args: argparse.Namespace) -> Agent:
    if args.agent == "llm":
        var = "OPENROUTER_API_KEY" if args.provider == "openrouter" else "OPENAI_API_KEY"
        if not os.environ.get(var):
            raise SystemExit(f"{var} is not set. --agent llm needs it (or use the offline agent).")
        from .llm_agent import LLMAgent

        return LLMAgent(model=args.model, provider=args.provider)
    return HeuristicAgent()


def _add_agent_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--agent", choices=["heuristic", "llm"], default="heuristic")
    p.add_argument("--provider", choices=["openai", "openrouter"], default="openai")
    p.add_argument("--model", default="gpt-4o")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contract-gap-eval",
        description="Contract-vs-policy gap analysis + a gap-recall reliability harness.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Produce the gap matrix for contracts.")
    _add_agent_flags(check)
    check.add_argument("--contract", help="A single contract id (default: all).")
    check.add_argument("--json", help="Write the matrix/matrices as JSON to this path.")

    rel = sub.add_parser("reliability", help="Measure the agent against the gold set.")
    _add_agent_flags(rel)

    cal = sub.add_parser("calibrate", help="Measure the evidence-relevance judge.")
    cal.add_argument("--judge", choices=["static"], default="static")

    args = parser.parse_args(argv)

    if args.command == "check":
        agent = _build_agent(args)
        contracts = [get_contract(args.contract)] if args.contract else CONTRACTS
        reports = [analyze_contract(agent, c) for c in contracts]
        for report in reports:
            print(render_contract_report(report))
            print()
        total_gaps = sum(len(r.gaps) for r in reports)
        print(f"Total: {total_gaps} écart(s) sur {len(contracts)} contrat(s).")
        if args.json:
            payload = [r.model_dump(mode="json") for r in reports]
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            print(f"\nJSON écrit dans {args.json}")
        return 0

    if args.command == "reliability":
        agent = _build_agent(args)
        rel_report = evaluate_reliability(agent, build_gold_set())
        print(render_reliability_report(rel_report))
        # CI gate: fail only on a missed CRITICAL gap (the ship-blocker a legal
        # team cares about). A missed minor/major is reported but does not fail
        # the build — so the honest 88% baseline passes while a lax agent that
        # misses a critical gap does not.
        return 1 if rel_report.critical_missed > 0 else 0

    if args.command == "calibrate":
        calib = calibrate_judge(StaticRelevanceJudge(), GROUND_GOLD)
        print(f"Calibration du juge « {calib.judge_name} »")
        print(f"  Accord: {calib.agreement_rate * 100:.0f}% ({calib.agree}/{calib.total})")
        print(f"  Faux positifs: {calib.false_positive}   Faux négatifs: {calib.false_negative}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
