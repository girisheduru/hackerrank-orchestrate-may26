"""E2E tests: full run produces a valid output.csv meeting the submission contract."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from ticket_io.csv_writer import OUTPUT_FIELDS
from ticket_io.csv_reader import read_tickets
from orchestrator.pipeline import TriagePipeline
from ticket_io.csv_writer import write_results


NEEDS_API = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@NEEDS_API
def test_e2e_full_run_produces_valid_csv(tickets_csv, output_csv, data_dir):
    """End-to-end: process all tickets, write output, verify contract."""
    pipeline = TriagePipeline(data_dir=data_dir, seed=42)
    tickets = read_tickets(tickets_csv)
    results = [pipeline.process_ticket(t) for t in tickets]
    write_results(results, output_csv)

    assert output_csv.exists(), "output.csv was not created"

    with output_csv.open() as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    # Correct column headers
    assert list(reader.fieldnames) == OUTPUT_FIELDS or set(OUTPUT_FIELDS) == set(reader.fieldnames)

    # All rows present
    assert len(rows) == len(tickets), f"Expected {len(tickets)} rows, got {len(rows)}"

    # Valid enum values throughout
    valid_statuses = {"replied", "escalated"}
    valid_types = {"product_issue", "feature_request", "bug", "invalid"}
    for row in rows:
        assert row["status"] in valid_statuses, f"Bad status: {row['status']}"
        assert row["request_type"] in valid_types, f"Bad type: {row['request_type']}"
        assert row["response"].strip(), "Empty response"
        assert row["justification"].strip(), "Empty justification"
        assert row["product_area"].strip(), "Empty product_area"

    # At least one escalation
    escalated = [r for r in rows if r["status"] == "escalated"]
    assert len(escalated) >= 1, "Expected at least one escalation"


def test_output_fields_constant():
    """OUTPUT_FIELDS must contain exactly the required 8 columns."""
    required = {"issue", "subject", "company", "response", "product_area", "status", "request_type", "justification"}
    assert set(OUTPUT_FIELDS) == required
