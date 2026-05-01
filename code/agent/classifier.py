"""Company inference and product area classification."""

from __future__ import annotations

import re

# Keyword maps for company inference when Company == "None"
_COMPANY_KEYWORDS: dict[str, list[str]] = {
    "hackerrank": [
        "hackerrank", "hacker rank", "assessment", "test score", "coding test",
        "recruiter", "mock interview", "resume builder", "candidate", "hiring",
        "proctoring", "submissions", "challenge", "certificate",
    ],
    "claude": [
        "claude", "anthropic", "claude.ai", "bedrock", "ai model", "lti",
        "mcp", "operator", "usage policy", "model crawl", "claude code",
        "claude api", "workspace", "claude team",
    ],
    "visa": [
        "visa", "visa card", "credit card", "debit card", "traveller",
        "card blocked", "cardholder", "merchant", "dispute charge",
        "chargeback", "minimum spend", "atm",
    ],
}

# Corpus breadcrumb → product_area label maps per company
_HACKERRANK_AREAS = {
    "screen": "screen",
    "interviews": "interviews",
    "library": "library",
    "chakra": "chakra",
    "skillup": "skillup",
    "engage": "engage",
    "integrations": "integrations",
    "settings": "settings",
    "general": "general_help",
    "community": "hackerrank_community",
}

_CLAUDE_AREAS = {
    "privacy": "privacy_and_legal",
    "legal": "privacy_and_legal",
    "team": "team_and_enterprise",
    "enterprise": "team_and_enterprise",
    "billing": "billing",
    "api": "claude_api",
    "console": "claude_api",
    "bedrock": "claude_api",
    "safeguard": "safeguards",
    "connector": "connectors",
    "desktop": "claude_desktop",
    "mobile": "claude_mobile",
    "pro": "pro_and_max",
    "max": "pro_and_max",
    "education": "claude_for_education",
    "account": "account_management",
    "conversation": "conversation_management",
}

_VISA_AREAS = {
    "travel": "travel_support",
    "small.business": "small_business_support",
    "consumer": "general_support",
    "general": "general_support",
    "support": "general_support",
}


def infer_company(issue: str, subject: str, company: str) -> str:
    """
    Return the canonical company key (hackerrank | claude | visa | unknown)
    from ticket text when the declared Company is 'None' or empty.
    """
    if company.lower() not in ("none", "", "n/a"):
        return company.lower()

    combined = f"{subject} {issue}".lower()
    scores: dict[str, int] = {k: 0 for k in _COMPANY_KEYWORDS}
    for co, keywords in _COMPANY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                scores[co] += 1

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "unknown"


def classify_product_area(breadcrumbs: list[str], company: str) -> str:
    """
    Map corpus breadcrumbs to a product_area label for the given company.
    Falls back to a generic area if no match found.
    """
    company_key = company.lower()
    crumb_str = " ".join(breadcrumbs).lower()

    if company_key == "hackerrank":
        area_map = _HACKERRANK_AREAS
    elif company_key == "claude":
        area_map = _CLAUDE_AREAS
    elif company_key == "visa":
        area_map = _VISA_AREAS
    else:
        return "general"

    for keyword, area in area_map.items():
        if re.search(keyword, crumb_str):
            return area

    return "general"


def classify_request_type_heuristic(issue: str, subject: str) -> str:
    """
    Fallback heuristic when LLM is unavailable.
    Returns one of: product_issue | feature_request | bug | invalid
    """
    combined = f"{subject} {issue}".lower()

    invalid_signals = [
        r"iron man", r"delete all files", r"r.gle interne", r"reveal.*instruction",
        r"what is the name of", r"actor", r"thank you",
    ]
    for sig in invalid_signals:
        if re.search(sig, combined, re.I):
            return "invalid"

    if re.search(r"\b(feature|request|add|would like|wish|want you to|suggest)\b", combined):
        return "feature_request"

    if re.search(r"\b(bug|error|crash|broken|not working|fail|exception|500|404)\b", combined):
        return "bug"

    return "product_issue"
