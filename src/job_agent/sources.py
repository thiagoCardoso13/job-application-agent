"""Where emails come from: the synthetic demo set or a Gmail inbox (read-only)."""

from __future__ import annotations

import base64
import html
import re
from datetime import UTC, datetime
from typing import Protocol

from job_agent.demo_data import load_emails
from job_agent.models import Email

MAX_BODY_CHARS = 4000


class EmailSource(Protocol):
    def fetch(self) -> list[Email]: ...


class DemoSource:
    def fetch(self) -> list[Email]:
        return load_emails()


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to text/html stripped of tags."""
    plain: list[str] = []
    rich: list[str] = []

    def walk(part: dict) -> None:
        data = part.get("body", {}).get("data")
        mime = part.get("mimeType", "")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            rich.append(_html_to_text(_decode(data)))
        for child in part.get("parts", []):
            walk(child)

    walk(payload)
    text = "\n".join(plain) if plain else "\n".join(rich)
    return text.strip()[:MAX_BODY_CHARS]


def parse_message(msg: dict) -> Email:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    received = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=UTC).date()
    return Email(
        id=msg["id"],
        sender=headers.get("from", ""),
        subject=headers.get("subject", ""),
        received=received,
        body=extract_body(msg.get("payload", {})),
    )


class GmailSource:
    """Read-only: lists and reads messages, never modifies, sends or deletes anything."""

    def __init__(self, service=None, query: str = "newer_than:30d", max_results: int = 50):
        if service is None:
            from job_agent.google_auth import GMAIL_READONLY, build_service

            service = build_service("gmail", "v1", [GMAIL_READONLY])
        self.service = service
        self.query = query
        self.max_results = max_results

    def fetch(self) -> list[Email]:
        messages = self.service.users().messages()
        listing = messages.list(userId="me", q=self.query, maxResults=self.max_results).execute()
        emails = []
        for ref in listing.get("messages", []):
            msg = messages.get(userId="me", id=ref["id"], format="full").execute()
            emails.append(parse_message(msg))
        return emails
