"""Claude API responder with corpus-grounded prompting and rules-only fallback."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from retrieval.retriever import SearchResult


VALID_STATUSES = {"replied", "escalated"}
VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}

_SYSTEM_PROMPT = """\
You are a support triage agent for {company}. Your job is to classify and respond to support tickets.

STRICT RULES — you must follow every rule:
1. Base your response ONLY on the reference documents provided below. Do not use any external knowledge.
2. If the reference documents do not contain enough information to answer, set status="escalated".
3. Never fabricate policies, steps, procedures, phone numbers, or URLs not present in the documents.
4. For sensitive cases (fraud, identity theft, security vulnerabilities, account compromise, billing disputes, service outages), ALWAYS set status="escalated".
5. Use request_type="invalid" ONLY for requests completely unrelated to {company}'s products (e.g. entertainment trivia, harmful/illegal requests). A legitimate question that lacks enough corpus documentation should be "escalated", not "invalid".
6. Your justification MUST cite the specific document title or URL you used.

You must return a JSON object with exactly these fields:
{{
  "status": "replied" | "escalated",
  "product_area": "<concise area label from the document breadcrumbs>",
  "response": "<user-facing reply — grounded only in the provided documents>",
  "justification": "<cite the specific document(s) used, including title and/or URL>",
  "request_type": "product_issue" | "feature_request" | "bug" | "invalid"
}}
Return only valid JSON. No markdown fences, no extra keys.\
"""

_USER_PROMPT = """\
## Reference Documents ({company} Support Corpus)

{documents}

---

## Support Ticket

Subject: {subject}
Issue: {issue}

Triage this ticket following the rules in your system prompt. Return JSON only.\
"""


@dataclass
class LLMResponse:
    status: str
    product_area: str
    response: str
    justification: str
    request_type: str
    raw: str = ""


def _format_documents(results: list[SearchResult]) -> str:
    parts = []
    for i, r in enumerate(results, 1):
        crumbs = " > ".join(r.chunk.breadcrumbs) if r.chunk.breadcrumbs else ""
        parts.append(
            f"[Doc {i}] {r.chunk.title}\n"
            f"Breadcrumbs: {crumbs}\n"
            f"Source: {r.chunk.source_url}\n"
            f"---\n{r.chunk.text}\n"
        )
    return "\n".join(parts) if parts else "(No relevant documents found in corpus)"


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from model output, tolerating minor formatting issues."""
    raw = raw.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _validate_and_coerce(data: dict) -> dict:
    """Enforce enum constraints on the parsed response."""
    status = data.get("status", "escalated")
    if status not in VALID_STATUSES:
        status = "escalated"

    request_type = data.get("request_type", "product_issue")
    if request_type not in VALID_REQUEST_TYPES:
        request_type = "product_issue"

    return {
        "status": status,
        "product_area": str(data.get("product_area", "general")).strip() or "general",
        "response": str(data.get("response", "")).strip(),
        "justification": str(data.get("justification", "")).strip(),
        "request_type": request_type,
    }


def generate_response(
    issue: str,
    subject: str,
    company: str,
    retrieval_results: list[SearchResult],
    model: Optional[str] = None,
    seed: Optional[int] = None,
) -> LLMResponse:
    """
    Call Claude API with retrieved corpus chunks as grounding context.
    Falls back to rule-based classification if API key is unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _rule_based_fallback(issue, subject, company, retrieval_results)

    try:
        import anthropic
    except ImportError:
        return _rule_based_fallback(issue, subject, company, retrieval_results)

    model = model or os.environ.get("TRIAGE_LLM_MODEL", "claude-sonnet-4-6")
    company_display = company.title() if company.lower() != "unknown" else "the relevant support team"

    system = _SYSTEM_PROMPT.format(company=company_display)
    user = _USER_PROMPT.format(
        company=company_display,
        documents=_format_documents(retrieval_results),
        subject=subject or "(no subject)",
        issue=issue,
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    raw = message.content[0].text
    try:
        data = _parse_json_response(raw)
        coerced = _validate_and_coerce(data)
    except (json.JSONDecodeError, KeyError, IndexError):
        # JSON parse failure → escalate safely
        return LLMResponse(
            status="escalated",
            product_area="general",
            response="We were unable to process your request automatically. A support agent will follow up.",
            justification="LLM response parsing failed — escalating for safety.",
            request_type="product_issue",
            raw=raw,
        )

    return LLMResponse(raw=raw, **coerced)


def _rule_based_fallback(
    issue: str,
    subject: str,
    company: str,
    results: list[SearchResult],
) -> LLMResponse:
    """Deterministic fallback when Anthropic API is unavailable."""
    from agent.classifier import classify_request_type_heuristic, classify_product_area

    request_type = classify_request_type_heuristic(issue, subject)

    if results:
        top = results[0]
        product_area = classify_product_area(top.chunk.breadcrumbs, company)
        response = (
            f"Based on our support documentation, please refer to: {top.chunk.title}. "
            f"{top.chunk.text[:300].strip()}…"
        )
        justification = f"Retrieved from: {top.chunk.title} ({top.chunk.source_url})"
    else:
        product_area = "general"
        response = "We could not find relevant documentation for your query. A support agent will follow up."
        justification = "No relevant documents found in corpus — escalating."

    status = "replied" if results and results[0].score > 0.5 else "escalated"

    return LLMResponse(
        status=status,
        product_area=product_area,
        response=response,
        justification=justification,
        request_type=request_type,
        raw="(rule-based fallback)",
    )
