"""Integration tests: process sample_support_tickets.csv and verify known outcomes."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from ticket_io.csv_reader import read_tickets
from orchestrator.pipeline import TriagePipeline


# Skip integration tests if ANTHROPIC_API_KEY is not set (CI without key)
NEEDS_API = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping LLM integration tests",
)


@pytest.fixture(scope="module")
def pipeline(data_dir):
    return TriagePipeline(data_dir=data_dir, seed=42)


@pytest.fixture(scope="module")
def sample_results(pipeline, sample_csv):
    tickets = read_tickets(sample_csv)
    return [pipeline.process_ticket(t) for t in tickets]


@NEEDS_API
def test_sample_all_rows_processed(sample_results, sample_csv):
    tickets = read_tickets(sample_csv)
    assert len(sample_results) == len(tickets)


@NEEDS_API
def test_sample_status_values_valid(sample_results):
    for r in sample_results:
        assert r.status in ("replied", "escalated"), f"Invalid status: {r.status}"


@NEEDS_API
def test_sample_request_type_values_valid(sample_results):
    for r in sample_results:
        assert r.request_type in (
            "product_issue", "feature_request", "bug", "invalid"
        ), f"Invalid request_type: {r.request_type}"


@NEEDS_API
def test_sample_at_least_one_escalation(sample_results):
    """Sample data includes 'Site Down' which must be escalated."""
    escalated = [r for r in sample_results if r.status == "escalated"]
    assert len(escalated) >= 1, "Expected at least one escalation in sample data"


@NEEDS_API
def test_sample_out_of_scope_is_invalid(sample_results, sample_csv):
    """'What is the name of the actor in Iron Man?' → invalid."""
    tickets = read_tickets(sample_csv)
    for ticket, result in zip(tickets, sample_results):
        if "iron man" in ticket.issue.lower() or "actor" in ticket.issue.lower():
            assert result.request_type == "invalid", (
                f"Expected invalid for out-of-scope query, got {result.request_type}"
            )


@NEEDS_API
def test_sample_responses_non_empty(sample_results):
    for r in sample_results:
        assert r.response.strip(), f"Empty response for row {r.row_id}"


@NEEDS_API
def test_sample_justifications_non_empty(sample_results):
    for r in sample_results:
        assert r.justification.strip(), f"Empty justification for row {r.row_id}"
