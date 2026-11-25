"""Email classifiers: an LLM-based one and a keyword baseline for comparison."""

from __future__ import annotations

import re
from typing import Protocol

from job_agent.models import Category, Email, Extraction

SYSTEM_PROMPT = """You read emails received by a junior developer/data candidate who is job \
hunting in Spain. Emails are in English or Spanish. Extract structured data from ONE email.

category (pick exactly one):
- interview: invitation or scheduling of an interview, call or panel with a person.
- test: a take-home assignment or online assessment the candidate must complete.
- rejection: the company will not continue with the candidate, or the position was filled.
- info_request: the company asks the candidate for data, documents or answers.
- acknowledgement: automatic confirmation that the application was received.
- other: newsletters, job alerts, ads, events, personal or security emails.

company and role: exactly as written in the email; null when the email is not about one application.
due: the one date the candidate must act on or attend (interview date, deadline to submit or \
reply), as YYYY-MM-DD; null when there is none. Never invent a date. Ignore start dates \
mentioned only as context and event dates of "other" emails."""


class Classifier(Protocol):
    def classify(self, email: Email) -> Extraction: ...


def _render(email: Email) -> str:
    return (
        f"From: {email.sender}\nReceived: {email.received.isoformat()}\n"
        f"Subject: {email.subject}\n\n{email.body}"
    )


class LlmClassifier:
    """Structured-output classifier. Tries each model in order until one answers."""

    def __init__(self, llms: list):
        if not llms:
            raise ValueError("at least one model is required")
        self.chains = [llm.with_structured_output(Extraction) for llm in llms]

    def classify(self, email: Email) -> Extraction:
        messages = [("system", SYSTEM_PROMPT), ("human", _render(email))]
        last_error: Exception | None = None
        for chain in self.chains:
            try:
                result = chain.invoke(messages)
            except Exception as exc:  # quota, timeout, schema errors: try the next model
                last_error = exc
                continue
            if isinstance(result, Extraction):
                return result
            if isinstance(result, dict):
                return Extraction(**result)
        raise RuntimeError(f"all models failed: {last_error}")


# Deliberately generic first-match rules (not tuned on the demo set), so the comparison is fair.
_RULES: list[tuple[Category, re.Pattern[str]]] = [
    (Category.REJECTION, re.compile(r"unfortunately|lamentablemente|other candidates", re.I)),
    (Category.INTERVIEW, re.compile(r"interview|entrevista", re.I)),
    (Category.TEST, re.compile(r"assessment|assignment|prueba|test", re.I)),
    (Category.ACKNOWLEDGEMENT, re.compile(r"received|recibido|thanks for applying", re.I)),
]


class KeywordClassifier:
    """Naive regex baseline, only to show how much the LLM adds. Extracts the category only."""

    def classify(self, email: Email) -> Extraction:
        text = f"{email.subject}\n{email.body}"
        for category, pattern in _RULES:
            if pattern.search(text):
                return Extraction(category=category)
        return Extraction(category=Category.OTHER)
