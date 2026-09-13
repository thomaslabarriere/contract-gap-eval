"""Render the gap matrix (artifact) and the reliability report."""

from __future__ import annotations

from .models import ContractReport, GapStatus, ReliabilityReport, Severity
from .policy import get_rule
from .pricing import estimate_usd, model_from_name

_MARK = {GapStatus.COMPLIANT: "OK ", GapStatus.GAP: "!! ", GapStatus.NOT_APPLICABLE: "-- "}
_SEV_ORDER = [Severity.CRITICAL, Severity.MAJOR, Severity.MINOR]


def render_contract_report(report: ContractReport) -> str:
    bar = "─" * 68
    lines = [bar, f"Matrice d'écarts: {report.title} [{report.contract_id}]", bar]
    lines.append(f"Écarts: {len(report.gaps)} / {len(report.verdicts)} règles vérifiées")
    lines.append("")
    for v in report.verdicts:
        rule = get_rule(v.rule_id)
        tag = f"({rule.severity.value})" if v.status is GapStatus.GAP else ""
        lines.append(f"{_MARK[v.status]}{v.rule_id:<9} {rule.title} {tag}")
        if v.evidence:
            lines.append(f"      preuve: « {v.evidence} »")
        if v.explanation:
            lines.append(f"      {v.explanation}")
    lines.append(bar)
    return "\n".join(lines)


def render_reliability_report(rel: ReliabilityReport) -> str:
    bar = "─" * 68
    lines = [bar, f"Fiabilité de l'agent: {rel.agent_name}", bar]
    lines.append(
        f"Gap-recall: {rel.gap_recall * 100:.0f}% "
        f"({rel.caught_gaps}/{rel.true_gaps} écarts détectés)   "
        f"Précision: {rel.precision * 100:.0f}%"
    )
    lines.append(f"Écarts manqués: {rel.missed_gaps} (dont critiques: {rel.critical_missed})")
    lines.append(
        f"Fausses alertes: {rel.false_alarms}   "
        f"Citations hallucinées: {rel.hallucinated_citations}"
    )
    lines.append("")

    lines.append("Recall par sévérité")
    for sev in _SEV_ORDER:
        caught, true = rel.recall_by_severity.get(sev, (0, 0))
        if true:
            lines.append(f"  {sev.value:<9} {caught / true * 100:>3.0f}%  ({caught}/{true})")
    lines.append("")
    lines.append(f"Accord global: {rel.agreement_rate * 100:.0f}% ({rel.agree}/{rel.total})")

    tokens = rel.prompt_tokens + rel.completion_tokens
    if tokens > 0:
        lines.append("")
        lines.append("Coût & latence")
        usd = estimate_usd(
            model_from_name(rel.agent_name), rel.prompt_tokens, rel.completion_tokens
        )
        cost = f"  Tokens: {tokens}"
        if usd is not None:
            cost += f"   Coût estimé: ${usd:.4f} (prix catalogue indicatif)"
        lines.append(cost)
        if rel.total:
            lines.append(f"  Latence: {rel.total_latency_ms / rel.total:.0f} ms/règle")

    lines.append(bar)
    return "\n".join(lines)
