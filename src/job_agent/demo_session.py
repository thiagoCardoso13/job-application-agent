"""State of one demo visitor: tracker, review queue, timeline and the AI-call budget."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from job_agent.agent import run_agent
from job_agent.models import Email
from job_agent.tracker import CsvTracker


class LimitReached(RuntimeError):
    pass


class DemoSession:
    def __init__(self, today: date, max_llm_calls: int = 10):
        self.today = today
        self.max_llm_calls = max_llm_calls
        self.llm_calls = 0
        self.tracker = CsvTracker(Path(tempfile.mkdtemp()) / "tracker.csv")
        self.log: list[str] = []
        self.review: list[dict] = []
        self.drafts: dict[str, str] = {}

    def spend_call(self) -> None:
        if self.llm_calls >= self.max_llm_calls:
            raise LimitReached(f"demo limit of {self.max_llm_calls} AI calls reached")
        self.llm_calls += 1

    def run(self, emails: list[Email], classifier, label: str, metered: bool) -> None:
        """Run the agent. With metered=True every email costs one call from the budget."""
        session = self

        class Gate:
            def classify(self, email):
                if metered:
                    session.spend_call()
                return classifier.classify(email)

        state = run_agent(emails, Gate(), self.tracker, today=self.today)
        self.log.append(f"classify: {len(emails)} email(s) via {label}")
        self.log.extend(f"tracker: {u}" for u in state.get("updated", []))
        self.log.extend(f"ignored: {i}" for i in state.get("ignored", []))
        self.review.extend(state.get("review", []))
