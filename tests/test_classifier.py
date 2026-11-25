from datetime import date

import pytest

from job_agent.classifier import KeywordClassifier, LlmClassifier
from job_agent.demo_data import load_labelled_emails
from job_agent.models import Category, Email, Extraction


def email():
    return Email(id="x", sender="a@b.c", subject="s", received=date(2026, 11, 1), body="b")


class FakeChain:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def invoke(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class FakeLlm:
    def __init__(self, chain):
        self.chain = chain

    def with_structured_output(self, schema):
        assert schema is Extraction
        return self.chain


def test_llm_classifier_returns_extraction():
    exp = Extraction(category=Category.INTERVIEW, company="Acme", role="Dev")
    assert LlmClassifier([FakeLlm(FakeChain(exp))]).classify(email()) == exp


def test_llm_classifier_accepts_dict_result():
    out = LlmClassifier([FakeLlm(FakeChain({"category": "test"}))]).classify(email())
    assert out.category is Category.TEST


def test_falls_back_to_next_model_on_error():
    bad = FakeChain(error=RuntimeError("quota"))
    good = FakeChain(Extraction(category=Category.OTHER))
    out = LlmClassifier([FakeLlm(bad), FakeLlm(good)]).classify(email())
    assert out.category is Category.OTHER
    assert bad.calls == 1 and good.calls == 1


def test_raises_when_all_models_fail():
    clf = LlmClassifier([FakeLlm(FakeChain(error=RuntimeError("quota")))])
    with pytest.raises(RuntimeError):
        clf.classify(email())


def test_keyword_baseline_beats_chance_but_is_imperfect():
    items = load_labelled_emails()
    preds = [KeywordClassifier().classify(i.email).category for i in items]
    acc = sum(p is i.expected.category for p, i in zip(preds, items, strict=True)) / len(items)
    assert 0.5 < acc < 1.0
