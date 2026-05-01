"""Read support tickets from CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class Ticket:
    row_id: int
    issue: str
    subject: str
    company: str  # HackerRank | Claude | Visa | None


def read_tickets(path: Path) -> list[Ticket]:
    tickets: list[Ticket] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            tickets.append(
                Ticket(
                    row_id=idx,
                    issue=(row.get("Issue") or "").strip(),
                    subject=(row.get("Subject") or "").strip(),
                    company=(row.get("Company") or "None").strip(),
                )
            )
    return tickets
