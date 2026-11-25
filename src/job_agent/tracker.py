"""Application tracker. CSV backend for demo/tests; Sheets comes later (same interface)."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from job_agent.models import Application, Category

FIELDS = ["company", "role", "status", "next_action", "due", "last_update"]


class Tracker(Protocol):
    def upsert(self, app: Application) -> None: ...
    def all(self) -> list[Application]: ...
    def stale(self, today: date, days: int) -> list[Application]: ...


class CsvTracker:
    """Rows are keyed by (company, role), case-insensitive."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def _key(app: Application) -> tuple[str, str]:
        return app.company.strip().lower(), app.role.strip().lower()

    def all(self) -> list[Application]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as f:
            return [
                Application(
                    company=r["company"],
                    role=r["role"],
                    status=Category(r["status"]),
                    next_action=r["next_action"],
                    due=date.fromisoformat(r["due"]) if r["due"] else None,
                    last_update=date.fromisoformat(r["last_update"]),
                )
                for r in csv.DictReader(f)
            ]

    def _write(self, apps: list[Application]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            for a in apps:
                writer.writerow(
                    {
                        "company": a.company,
                        "role": a.role,
                        "status": a.status.value,
                        "next_action": a.next_action,
                        "due": a.due.isoformat() if a.due else "",
                        "last_update": a.last_update.isoformat(),
                    }
                )

    def upsert(self, app: Application) -> None:
        apps = self.all()
        for i, existing in enumerate(apps):
            if self._key(existing) == self._key(app):
                apps[i] = app
                break
        else:
            apps.append(app)
        self._write(apps)

    def stale(self, today: date, days: int) -> list[Application]:
        """Applications still waiting (acknowledged only) with no news for `days` days."""
        cutoff = today - timedelta(days=days)
        return [
            a
            for a in self.all()
            if a.status is Category.ACKNOWLEDGEMENT and a.last_update <= cutoff
        ]
