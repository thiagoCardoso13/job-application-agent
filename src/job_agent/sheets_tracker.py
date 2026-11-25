"""Google Sheets backend for the tracker. Same behaviour as CsvTracker, rows live in a sheet."""

from __future__ import annotations

from datetime import date

from job_agent.models import Application, Category
from job_agent.tracker import FIELDS, CsvTracker


class SheetsTracker(CsvTracker):
    """Reuses the upsert/stale logic of CsvTracker; only reading and writing change."""

    def __init__(self, spreadsheet_id: str, tab: str = "Applications", service=None):
        if service is None:
            from job_agent.google_auth import SHEETS, build_service

            service = build_service("sheets", "v4", [SHEETS])
        self.service = service
        self.spreadsheet_id = spreadsheet_id
        self.range = f"{tab}!A:F"

    @property
    def _values(self):
        return self.service.spreadsheets().values()

    def all(self) -> list[Application]:
        rows = self._values.get(spreadsheetId=self.spreadsheet_id, range=self.range).execute()
        apps = []
        for row in rows.get("values", [])[1:]:  # first row is the header
            row = row + [""] * (len(FIELDS) - len(row))
            company, role, status, next_action, due, last_update = row[:6]
            apps.append(
                Application(
                    company=company,
                    role=role,
                    status=Category(status),
                    next_action=next_action,
                    due=date.fromisoformat(due) if due else None,
                    last_update=date.fromisoformat(last_update),
                )
            )
        return apps

    def _write(self, apps: list[Application]) -> None:
        values = [FIELDS] + [
            [
                a.company,
                a.role,
                a.status.value,
                a.next_action,
                a.due.isoformat() if a.due else "",
                a.last_update.isoformat(),
            ]
            for a in apps
        ]
        # Upserts never remove rows, so overwriting from A1 is enough (nothing is cleared first).
        self._values.update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{self.range.split('!')[0]}!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
