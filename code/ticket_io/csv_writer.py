"""Write triage results to output CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


StatusType = Literal["replied", "escalated"]
RequestType = Literal["product_issue", "feature_request", "bug", "invalid"]

OUTPUT_FIELDS = [
    "issue", "subject", "company",
    "response", "product_area", "status", "request_type", "justification",
]


@dataclass
class TriageResult:
    row_id: int
    issue: str
    subject: str
    company: str
    status: StatusType
    product_area: str
    response: str
    justification: str
    request_type: RequestType
    retrieval_sources: list[str]
    confidence: float = 1.0


def write_results(results: list[TriageResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for r in sorted(results, key=lambda x: x.row_id):
            writer.writerow({
                "issue": r.issue,
                "subject": r.subject,
                "company": r.company,
                "response": r.response,
                "product_area": r.product_area,
                "status": r.status,
                "request_type": r.request_type,
                "justification": r.justification,
            })
