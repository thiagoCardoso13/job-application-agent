"""Replay of real model answers saved by scripts/precompute.py (keeps the demo free)."""

from __future__ import annotations

import json
from pathlib import Path

from job_agent.models import Email, Extraction

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "demo_data" / "precomputed.json"


class ReplayClassifier:
    def __init__(self, answers: dict[str, dict]):
        self.answers = answers

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> ReplayClassifier | None:
        if not path.exists():
            return None
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def classify(self, email: Email) -> Extraction:
        return Extraction(**self.answers[email.id])
