from datetime import date

from job_agent.agent import run_agent
from job_agent.models import Application, Category, Email, Extraction
from job_agent.tracker import CsvTracker


def mail(id_, received, subject="s"):
    return Email(id=id_, sender="a@b.c", subject=subject, received=received, body=id_)


class ScriptedClassifier:
    """Returns the extraction registered for the email id (stands in for the LLM)."""

    def __init__(self, table):
        self.table = table

    def classify(self, email):
        out = self.table[email.id]
        if isinstance(out, Exception):
            raise out
        return out


class FakeLlm:
    def invoke(self, messages):
        class R:
            content = "Hello, just following up. [Your name]"

        return R()


def ext(cat, company="Acme", role="Dev", due=None):
    return Extraction(category=cat, company=company, role=role, due=due)


def test_new_application_is_added(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    state = run_agent(
        [mail("1", date(2026, 11, 2))],
        ScriptedClassifier({"1": ext(Category.ACKNOWLEDGEMENT)}),
        t,
        today=date(2026, 11, 3),
    )
    assert [a.status for a in t.all()] == [Category.ACKNOWLEDGEMENT]
    assert state["updated"] == ["Acme / Dev: acknowledgement"]


def test_status_moves_forward_but_never_back(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    # Interview arrives first by date, then a late "application received" email.
    emails = [mail("late-ack", date(2026, 11, 9)), mail("iv", date(2026, 11, 5))]
    table = {
        "iv": ext(Category.INTERVIEW, due=date(2026, 11, 12)),
        "late-ack": ext(Category.ACKNOWLEDGEMENT),
    }
    state = run_agent(emails, ScriptedClassifier(table), t, today=date(2026, 11, 10))
    app = t.all()[0]
    assert app.status is Category.INTERVIEW
    assert app.due == date(2026, 11, 12)
    assert state["ignored"] == ["late-ack"]


def test_rejection_is_final(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    emails = [mail("rej", date(2026, 11, 5)), mail("iv", date(2026, 11, 6))]
    table = {"rej": ext(Category.REJECTION), "iv": ext(Category.INTERVIEW)}
    run_agent(emails, ScriptedClassifier(table), t, today=date(2026, 11, 7))
    assert t.all()[0].status is Category.REJECTION


def test_other_emails_do_not_touch_tracker(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    state = run_agent(
        [mail("n", date(2026, 11, 2))],
        ScriptedClassifier({"n": Extraction(category=Category.OTHER)}),
        t,
        today=date(2026, 11, 3),
    )
    assert t.all() == []
    assert state["ignored"] == ["n"]


def test_missing_company_goes_to_review_queue(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    state = run_agent(
        [mail("x", date(2026, 11, 2))],
        ScriptedClassifier({"x": Extraction(category=Category.INTERVIEW, company="Acme")}),
        t,
        today=date(2026, 11, 3),
    )
    assert t.all() == []
    assert state["review"] == [{"email_id": "x", "reason": "company or role missing"}]


def test_classifier_failure_does_not_stop_the_run(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    emails = [mail("bad", date(2026, 11, 2)), mail("ok", date(2026, 11, 3))]
    table = {"bad": RuntimeError("quota"), "ok": ext(Category.TEST, due=date(2026, 11, 9))}
    state = run_agent(emails, ScriptedClassifier(table), t, today=date(2026, 11, 4))
    assert [a.status for a in t.all()] == [Category.TEST]
    assert state["review"][0]["email_id"] == "bad"
    assert "quota" in state["review"][0]["reason"]


def test_followups_due_soon_and_stale_with_drafts(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    t.upsert(
        Application(
            company="Quiet", role="Dev", status=Category.ACKNOWLEDGEMENT,
            last_update=date(2026, 11, 1),
        )
    )
    t.upsert(
        Application(
            company="Soon", role="Dev", status=Category.INTERVIEW, due=date(2026, 11, 21),
            last_update=date(2026, 11, 18),
        )
    )
    t.upsert(
        Application(
            company="Far", role="Dev", status=Category.TEST, due=date(2026, 12, 30),
            last_update=date(2026, 11, 18),
        )
    )
    state = run_agent([], ScriptedClassifier({}), t, llm=FakeLlm(), today=date(2026, 11, 20))
    assert [a.company for a in state["due_soon"]] == ["Soon"]
    assert [a.company for a in state["stale"]] == ["Quiet"]
    assert state["drafts"] == {"Quiet": "Hello, just following up. [Your name]"}


def test_no_drafts_without_llm(tmp_path):
    t = CsvTracker(tmp_path / "t.csv")
    t.upsert(
        Application(
            company="Quiet", role="Dev", status=Category.ACKNOWLEDGEMENT,
            last_update=date(2026, 11, 1),
        )
    )
    state = run_agent([], ScriptedClassifier({}), t, today=date(2026, 11, 20))
    assert state["drafts"] == {}


def test_failed_draft_is_reported_not_fatal(tmp_path):
    class BrokenLlm:
        def invoke(self, messages):
            raise RuntimeError("503")

    t = CsvTracker(tmp_path / "t.csv")
    t.upsert(
        Application(
            company="Quiet", role="Dev", status=Category.ACKNOWLEDGEMENT,
            last_update=date(2026, 11, 1),
        )
    )
    state = run_agent([], ScriptedClassifier({}), t, llm=BrokenLlm(), today=date(2026, 11, 20))
    assert state["drafts"] == {}
    assert state["review"][0]["email_id"] == "followup:Quiet"
