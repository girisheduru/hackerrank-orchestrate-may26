"""Structured NDJSON logger for triage runs."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


class TriageLogger:
    """
    Writes structured log events as NDJSON lines to stderr (and optionally a file).
    Each event: {"ts": ISO, "level": "info|debug|warn|error", "job_id": ..., "msg": ...}
    """

    def __init__(self, job_id: str, verbose: bool = False, log_dir: Path | None = None):
        self.job_id = job_id
        self.verbose = verbose
        self._file = None

        level_env = os.environ.get("TRIAGE_LOG_LEVEL", "info").lower()
        self._debug_enabled = verbose or level_env == "debug"

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{job_id}.ndjson"
            self._file = log_path.open("a", encoding="utf-8")

    def _emit(self, level: str, msg: str) -> None:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "job_id": self.job_id,
            "msg": msg,
        }
        line = json.dumps(event, ensure_ascii=False)
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()
        if self.verbose or level in ("warn", "error"):
            print(line, file=sys.stderr)

    def info(self, msg: str) -> None:
        self._emit("info", msg)

    def debug(self, msg: str) -> None:
        if self._debug_enabled:
            self._emit("debug", msg)

    def warn(self, msg: str) -> None:
        self._emit("warn", msg)

    def error(self, msg: str) -> None:
        self._emit("error", msg)

    def __del__(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
