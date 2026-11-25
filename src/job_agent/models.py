"""Data models shared by the classifier, the agent and the trackers."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class Category(StrEnum):
    INTERVIEW = "interview"
    TEST = "test"
    REJECTION = "rejection"
    INFO_REQUEST = "info_request"
    ACKNOWLEDGEMENT = "acknowledgement"
    OTHER = "other"


class Email(BaseModel):
    id: str
    sender: str
    subject: str
    received: date
    body: str
    lang: str = "en"


class Extraction(BaseModel):
    """What the classifier must produce for one email."""

    category: Category
    company: str | None = None
    role: str | None = None
    due: date | None = None


class LabelledEmail(BaseModel):
    """A demo email together with its expected extraction (for evals)."""

    email: Email
    expected: Extraction


class Application(BaseModel):
    """One row of the tracker."""

    company: str
    role: str
    status: Category
    next_action: str = ""
    due: date | None = None
    last_update: date
