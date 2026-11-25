"""Follow-up logic: deadlines coming up, applications gone quiet, and drafted messages.

Drafts are text only. The agent never sends email.
"""

from __future__ import annotations

from datetime import date, timedelta

from job_agent.models import Application, Category

ACTIONABLE = {Category.INTERVIEW, Category.TEST, Category.INFO_REQUEST}

FOLLOWUP_PROMPT = """Write a short, polite follow-up email (max 90 words) from a junior candidate \
to a recruiter. Company: {company}. Role: {role}. The candidate applied or last heard back \
{days} days ago and has had no reply. Use ONLY the facts given above: do not describe the \
company, its products or work, and do not claim any skills or experience. Plain text, no subject \
line, no placeholders other than the signature name [Your name]."""


def due_soon(apps: list[Application], today: date, hours: int = 48) -> list[Application]:
    """Open actions (interview, test, info request) whose date falls within the window."""
    limit = today + timedelta(hours=hours)
    return [
        a
        for a in apps
        if a.status in ACTIONABLE and a.due is not None and today <= a.due <= limit
    ]


def draft_followup(llm, app: Application, today: date) -> str:
    days = (today - app.last_update).days
    prompt = FOLLOWUP_PROMPT.format(company=app.company, role=app.role, days=days)
    reply = llm.invoke([("human", prompt)])
    content = getattr(reply, "content", reply)
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content).strip()
