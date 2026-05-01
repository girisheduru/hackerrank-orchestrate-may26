"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure code/ is importable during tests
CODE_DIR = Path(__file__).parent.parent.resolve()
REPO_ROOT = CODE_DIR.parent.resolve()

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import pytest
from ticket_io.csv_reader import Ticket


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def data_dir(repo_root) -> Path:
    return repo_root / "data"


@pytest.fixture
def sample_csv(repo_root) -> Path:
    return repo_root / "support_tickets" / "sample_support_tickets.csv"


@pytest.fixture
def tickets_csv(repo_root) -> Path:
    return repo_root / "support_tickets" / "support_tickets.csv"


@pytest.fixture
def output_csv(tmp_path) -> Path:
    return tmp_path / "output.csv"


@pytest.fixture
def make_ticket():
    def _make(issue="test issue", subject="test subject", company="HackerRank", row_id=0):
        return Ticket(row_id=row_id, issue=issue, subject=subject, company=company)
    return _make
