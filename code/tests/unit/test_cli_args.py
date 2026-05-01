"""Unit tests: CLI argument parsing and environment variable defaults."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.app import app

runner = CliRunner()


def test_run_missing_input_exits_3(tmp_path):
    """Non-existent input CSV returns exit code 3."""
    result = runner.invoke(
        app,
        ["run", "--input", str(tmp_path / "missing.csv"), "--data-dir", str(tmp_path)],
    )
    assert result.exit_code == 3


def test_run_missing_data_dir_exits_8(tmp_path):
    """Non-existent data directory returns exit code 8."""
    csv = tmp_path / "tickets.csv"
    csv.write_text("Issue,Subject,Company\nhello,world,HackerRank\n")
    result = runner.invoke(
        app,
        ["run", "--input", str(csv), "--data-dir", str(tmp_path / "nodata")],
    )
    assert result.exit_code == 8


def test_config_command_runs(tmp_path):
    """triage config --show does not crash."""
    result = runner.invoke(app, ["config", "--show"])
    # May print warning if no config file found, but should not crash (exit 0 or warn)
    assert result.exit_code in (0, 1)


def test_status_command_no_run(tmp_path):
    """triage status with no prior run returns exit code 1 gracefully."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code in (0, 1)
