"""Unit tests: output enum validation and CSV writer contract."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ticket_io.csv_writer import TriageResult, write_results, OUTPUT_FIELDS


def _make_result(**kwargs) -> TriageResult:
    defaults = dict(
        row_id=0,
        issue="test issue",
        subject="test subject",
        company="HackerRank",
        status="replied",
        product_area="screen",
        response="Test response",
        justification="Test justification from doc X",
        request_type="product_issue",
        retrieval_sources=["https://example.com"],
        confidence=0.8,
    )
    defaults.update(kwargs)
    return TriageResult(**defaults)


def test_output_csv_has_correct_headers(tmp_path):
    out = tmp_path / "output.csv"
    write_results([_make_result()], out)
    with out.open() as fh:
        reader = csv.DictReader(fh)
        assert list(reader.fieldnames) == OUTPUT_FIELDS


def test_output_csv_status_values(tmp_path):
    out = tmp_path / "output.csv"
    results = [
        _make_result(row_id=0, status="replied"),
        _make_result(row_id=1, status="escalated"),
    ]
    write_results(results, out)
    with out.open() as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    statuses = {r["status"] for r in rows}
    assert statuses <= {"replied", "escalated"}


def test_output_csv_request_type_values(tmp_path):
    out = tmp_path / "output.csv"
    results = [
        _make_result(row_id=i, request_type=rt)
        for i, rt in enumerate(["product_issue", "feature_request", "bug", "invalid"])
    ]
    write_results(results, out)
    with out.open() as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    types = {r["request_type"] for r in rows}
    assert types <= {"product_issue", "feature_request", "bug", "invalid"}


def test_output_rows_sorted_by_row_id(tmp_path):
    out = tmp_path / "output.csv"
    results = [_make_result(row_id=i, issue=f"issue {i}") for i in [2, 0, 1]]
    write_results(results, out)
    with out.open() as fh:
        reader = csv.DictReader(fh)
        issues = [r["issue"] for r in reader]
    assert issues == ["issue 0", "issue 1", "issue 2"]
