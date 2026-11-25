from datetime import date

import pytest

from job_agent.demo_data import load_emails
from job_agent.demo_session import DemoSession, LimitReached
from job_agent.models import Category, Extraction
from job_agent.replay import ReplayClassifier


class Fake:
    def classify(self, email):
        return Extraction(category=Category.TEST, company=f"C-{email.id}", role="Dev")


def test_metered_run_spends_budget_and_stops_at_limit():
    s = DemoSession(date(2026, 11, 20), max_llm_calls=2)
    emails = load_emails()[:3]
    s.run(emails, Fake(), "fake", metered=True)
    assert s.llm_calls == 2
    assert len(s.tracker.all()) == 2  # the third email hit the limit
    assert len(s.review) == 1 and "limit" in s.review[0]["reason"]


def test_unmetered_run_is_free():
    s = DemoSession(date(2026, 11, 20), max_llm_calls=0)
    s.run(load_emails()[:5], Fake(), "replay", metered=False)
    assert s.llm_calls == 0 and len(s.tracker.all()) == 5
    assert s.log[0].startswith("classify: 5")


def test_spend_call_raises():
    s = DemoSession(date(2026, 11, 20), max_llm_calls=0)
    with pytest.raises(LimitReached):
        s.spend_call()


def test_replay_classifier_roundtrip(tmp_path):
    import json

    path = tmp_path / "p.json"
    path.write_text(json.dumps({"e01": {"category": "interview", "company": "A", "role": "B"}}))
    out = ReplayClassifier.load(path).classify(load_emails()[0])
    assert out.category is Category.INTERVIEW
    assert ReplayClassifier.load(tmp_path / "missing.json") is None
