"""JSONL-based run metadata store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ticket_io.csv_writer import TriageResult

_DEFAULT_STORE_DIR = Path.home() / "hackerrank_orchestrate" / "runs"


class RunStore:
    """
    Persists per-row results and job metadata as JSONL files under the store dir.
    One file per job: <job_id>.jsonl
    """

    def __init__(self, store_dir: Path | None = None):
        self._dir = store_dir or _DEFAULT_STORE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._latest_job_id: Optional[str] = None

    def save_result(self, job_id: str, result: TriageResult) -> None:
        self._latest_job_id = job_id
        path = self._dir / f"{job_id}.jsonl"
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "row_id": result.row_id,
            "status": result.status,
            "product_area": result.product_area,
            "request_type": result.request_type,
            "confidence": result.confidence,
            "retrieval_sources": result.retrieval_sources,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_latest(self) -> Optional[dict]:
        if self._latest_job_id:
            return self.load(self._latest_job_id)
        # Find the most recently modified JSONL
        files = sorted(self._dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return None
        return self.load(files[0].stem)

    def load(self, job_id: str) -> Optional[dict]:
        path = self._dir / f"{job_id}.jsonl"
        if not path.exists():
            return None
        rows = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if not rows:
            return None
        return {
            "job_id": job_id,
            "total_rows": len(rows),
            "replied_count": sum(1 for r in rows if r.get("status") == "replied"),
            "escalated_count": sum(1 for r in rows if r.get("status") == "escalated"),
            "rows": rows,
        }

    def log_path(self, job_id: Optional[str] = None) -> Optional[Path]:
        if not job_id:
            files = sorted(self._dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
            return files[0] if files else None
        p = self._dir / f"{job_id}.jsonl"
        return p if p.exists() else None
