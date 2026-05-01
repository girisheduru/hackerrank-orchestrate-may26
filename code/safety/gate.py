"""Safety gate — pre- and post-process escalation rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class GateDecision:
    should_escalate: bool
    is_invalid: bool
    reason: str


# Patterns that always force escalation regardless of LLM output
_ESCALATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"identity.{0,10}(stolen|theft|compromised)", re.I), "identity theft/compromise"),
    (re.compile(r"(stolen|lost).{0,15}(card|wallet|passport)", re.I), "lost/stolen financial document"),
    (re.compile(r"\b(fraud|fraudulent)\b", re.I), "fraud indicator"),
    (re.compile(r"security.{0,15}(vulnerability|flaw|exploit|breach|bounty)", re.I), "security vulnerability report"),
    (re.compile(r"(site|platform|service).{0,10}(is |are )?(down|offline|unreachable|not working)", re.I), "service outage"),
    (re.compile(r"\b\w[\w\s]{0,20}(is|are)\s+down\b", re.I), "feature/platform down"),
    (re.compile(r"all.{0,20}(requests?|pages?|submissions?).{0,10}(fail|failing|broken|not working)", re.I), "widespread platform failure"),
    (re.compile(r"\b(refund|money back|reimburse|chargeback)\b", re.I), "billing/refund request"),
    (re.compile(r"\b(suspend|pause|cancel).{0,10}(subscription|account|plan)\b", re.I), "subscription cancellation"),
    (re.compile(r"restore.{0,30}access|not.{0,10}(workspace\s+)?(owner|admin)\b", re.I), "unauthorized account restoration"),
    (re.compile(r"\b(hack|hacked|compromised)\b.{0,20}(account|data|system)", re.I), "account compromise"),
    (re.compile(r"remove.{0,10}(access|seat|employee|user).{0,10}(immediately|asap|right now)", re.I), "urgent access removal"),
]

# Patterns that mark the ticket as invalid (out of scope / harmful)
# Use re.DOTALL so '.' matches newlines (important for multi-line ticket bodies)
_DOT = re.I | re.DOTALL
_INVALID_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(delete|remove|erase|wipe).{0,10}(all|every).{0,10}(file|data|record|directory)", _DOT), "destructive file operation"),
    (re.compile(r"(show|display|reveal|print|list).{0,30}(internal|system|private).{0,30}(rule|document|logic|prompt|instruction)", _DOT), "prompt injection / rule extraction"),
    # French/Spanish prompt injection: "affiche les règles internes / la logique"
    (re.compile(r"(affiche|montre|mostr[ae]).{0,50}(r[\xe8e]gle|document|logique|interne)", _DOT), "prompt injection (non-English)"),
    (re.compile(r"(ignore|disregard|forget).{0,20}(previous|prior|above|all).{0,10}(instruction|rule|constraint)", _DOT), "jailbreak attempt"),
    (re.compile(r"\bactor\b.{0,30}\b(iron man|movie|film|marvel)\b", re.I), "out of scope — entertainment query"),
    (re.compile(r"\b(illegal|weapon|explosive|drug)\b", re.I), "harmful/illegal content"),
]

# Patterns for low-information tickets that may need escalation
_VAGUE_PATTERN = re.compile(
    r"^(it.?s?\s+not\s+working[\s,]+help|it.?s?\s+not\s+working|help|help\s+me|help\s+needed|not\s+working|broken)[.!?,]?\s*$",
    re.I,
)


def pre_check(issue: str, subject: str, company: str) -> GateDecision:
    """
    Run before corpus retrieval and LLM.
    Returns a GateDecision if a hard rule fires; otherwise both flags are False.
    """
    combined = f"{subject} {issue}"

    for pattern, reason in _INVALID_PATTERNS:
        if pattern.search(combined):
            return GateDecision(should_escalate=False, is_invalid=True, reason=reason)

    for pattern, reason in _ESCALATE_PATTERNS:
        if pattern.search(combined):
            return GateDecision(should_escalate=True, is_invalid=False, reason=reason)

    # Vague single-line tickets with unknown/unresolved company → escalate
    if company.lower() in ("none", "", "unknown") and _VAGUE_PATTERN.match(issue.strip()):
        return GateDecision(should_escalate=True, is_invalid=False, reason="vague ticket with unknown company")

    return GateDecision(should_escalate=False, is_invalid=False, reason="")


def post_check(
    status: str,
    response: str,
    justification: str,
    retrieval_max_score: float,
    low_confidence_threshold: float = 0.10,
) -> GateDecision:
    """
    Run after LLM response.
    Escalates if retrieval confidence is too low or response looks hallucinated.
    """
    if retrieval_max_score < low_confidence_threshold and status == "replied":
        return GateDecision(
            should_escalate=True,
            is_invalid=False,
            reason=f"low retrieval confidence ({retrieval_max_score:.3f} < {low_confidence_threshold})",
        )

    # If the LLM itself decided to escalate, honour it
    if status == "escalated":
        return GateDecision(should_escalate=True, is_invalid=False, reason="LLM-decided escalation")

    return GateDecision(should_escalate=False, is_invalid=False, reason="")
