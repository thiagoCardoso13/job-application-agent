from datetime import date

from job_agent.models import Application, Category
from job_agent.sheets_tracker import SheetsTracker


class FakeExec:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class FakeSheets:
    """In-memory stand-in for the Sheets values API (one range)."""

    def __init__(self, values=None):
        self.values_store = values or []
        self.cleared = False

    def spreadsheets(self):
        return self

    def values(self):
        return self

    def get(self, spreadsheetId, range):
        return FakeExec(lambda: {"values": self.values_store} if self.values_store else {})

    def update(self, spreadsheetId, range, valueInputOption, body):
        assert range.endswith("!A1") and valueInputOption == "RAW"

        def run():
            self.values_store = body["values"]
            return {}

        return FakeExec(run)

    def clear(self, **kw):
        self.cleared = True
        return FakeExec(lambda: {})


def app(company="Acme", status=Category.ACKNOWLEDGEMENT, last=date(2026, 11, 1), due=None):
    return Application(company=company, role="Dev", status=status, last_update=last, due=due)


def test_empty_sheet_reads_as_no_applications():
    assert SheetsTracker("sid", service=FakeSheets()).all() == []


def test_upsert_writes_header_and_rows_then_updates_in_place():
    svc = FakeSheets()
    t = SheetsTracker("sid", service=svc)
    t.upsert(app())
    t.upsert(app(status=Category.INTERVIEW, last=date(2026, 11, 5), due=date(2026, 11, 9)))
    assert svc.values_store[0][:3] == ["company", "role", "status"]
    assert len(svc.values_store) == 2
    assert svc.values_store[1][2:] == ["interview", "", "2026-11-09", "2026-11-05"]
    assert not svc.cleared


def test_stale_uses_inherited_logic():
    t = SheetsTracker("sid", service=FakeSheets())
    t.upsert(app("Old", last=date(2026, 11, 1)))
    t.upsert(app("Fresh", last=date(2026, 11, 18)))
    assert [a.company for a in t.stale(date(2026, 11, 20), 10)] == ["Old"]
