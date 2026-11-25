from datetime import date

from job_agent.models import Application, Category
from job_agent.tracker import CsvTracker


def app(company="Acme", role="Dev", status=Category.ACKNOWLEDGEMENT, last=date(2026, 11, 1)):
    return Application(company=company, role=role, status=status, last_update=last)


def test_upsert_inserts_then_updates(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    t.upsert(app())
    t.upsert(app(company="ACME ", status=Category.INTERVIEW, last=date(2026, 11, 5)))
    rows = t.all()
    assert len(rows) == 1
    assert rows[0].status is Category.INTERVIEW


def test_roundtrip_keeps_due_date(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    a = app()
    a.due = date(2026, 11, 20)
    t.upsert(a)
    assert t.all()[0].due == date(2026, 11, 20)


def test_stale_only_returns_waiting_applications(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    t.upsert(app("Old", last=date(2026, 11, 1)))
    t.upsert(app("Fresh", last=date(2026, 11, 14)))
    t.upsert(app("Done", status=Category.REJECTION, last=date(2026, 11, 1)))
    stale = t.stale(today=date(2026, 11, 15), days=10)
    assert [a.company for a in stale] == ["Old"]
