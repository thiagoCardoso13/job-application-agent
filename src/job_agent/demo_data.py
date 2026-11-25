"""Loader for the synthetic demo emails."""

from __future__ import annotations

import json
from pathlib import Path

from job_agent.models import Email, Extraction, LabelledEmail

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "demo_data" / "emails.json"


def load_labelled_emails(path: Path = DEFAULT_PATH) -> list[LabelledEmail]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        LabelledEmail(
            email=Email(**{k: v for k, v in item.items() if k != "expected"}),
            expected=Extraction(**item["expected"]),
        )
        for item in raw
    ]


def load_emails(path: Path = DEFAULT_PATH) -> list[Email]:
    return [item.email for item in load_labelled_emails(path)]
