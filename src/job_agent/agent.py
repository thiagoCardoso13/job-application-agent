"""The agent: a LangGraph StateGraph that turns new emails into tracker updates.

fetch -> classify -> apply -> followups

- classify: the LLM extracts category/company/role/due from each email.
- apply: updates the tracker, or sends the email to the review queue when the data is unusable.
- followups: finds deadlines in the next 48 h and applications gone quiet, and drafts messages.

The agent only writes to the tracker. It never sends, deletes or labels email.
"""

from __future__ import annotations

import argparse
from datetime import date
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from job_agent.classifier import Classifier
from job_agent.followups import draft_followup, due_soon
from job_agent.models import Application, Category, Email, Extraction
from job_agent.tracker import Tracker

# A later stage never gets overwritten by an earlier one (an "application received" email
# arriving after an interview invitation must not reset the status). Rejection is final.
RANK = {
    Category.ACKNOWLEDGEMENT: 0,
    Category.INFO_REQUEST: 1,
    Category.TEST: 2,
    Category.INTERVIEW: 3,
    Category.REJECTION: 4,
}

NEXT_ACTION = {
    Category.INTERVIEW: "Attend interview",
    Category.TEST: "Complete the test",
    Category.INFO_REQUEST: "Reply with the requested information",
    Category.ACKNOWLEDGEMENT: "Wait for a reply",
    Category.REJECTION: "None (closed)",
}


class AgentState(TypedDict, total=False):
    emails: list[Email]
    today: date
    stale_days: int
    extractions: dict[str, Extraction]
    updated: list[str]  # human-readable log of tracker changes
    ignored: list[str]  # email ids that needed no tracker change
    review: list[dict]  # emails a human must look at: {"email_id", "reason"}
    due_soon: list[Application]
    stale: list[Application]
    drafts: dict[str, str]  # company -> drafted follow-up text


def build_agent(classifier: Classifier, tracker: Tracker, llm=None):
    """Wire the graph. `llm` is only needed to draft follow-ups."""

    def classify(state: AgentState) -> AgentState:
        extractions: dict[str, Extraction] = {}
        review = list(state.get("review", []))
        for email in sorted(state["emails"], key=lambda e: e.received):
            try:
                extractions[email.id] = classifier.classify(email)
            except Exception as exc:
                review.append({"email_id": email.id, "reason": f"classification failed: {exc}"})
        return {"extractions": extractions, "review": review}

    def apply(state: AgentState) -> AgentState:
        updated: list[str] = []
        ignored: list[str] = []
        review = list(state.get("review", []))
        by_id = {e.id: e for e in state["emails"]}
        for email_id, ext in state.get("extractions", {}).items():
            email = by_id[email_id]
            if ext.category is Category.OTHER:
                ignored.append(email_id)
                continue
            if not ext.company or not ext.role:
                review.append({"email_id": email_id, "reason": "company or role missing"})
                continue
            current = next(
                (
                    a
                    for a in tracker.all()
                    if (a.company.strip().lower(), a.role.strip().lower())
                    == (ext.company.strip().lower(), ext.role.strip().lower())
                ),
                None,
            )
            if current and RANK[ext.category] < RANK[current.status]:
                ignored.append(email_id)
                continue
            tracker.upsert(
                Application(
                    company=ext.company,
                    role=ext.role,
                    status=ext.category,
                    next_action=NEXT_ACTION[ext.category],
                    due=ext.due,
                    last_update=email.received,
                )
            )
            updated.append(f"{ext.company} / {ext.role}: {ext.category.value}")
        return {"updated": updated, "ignored": ignored, "review": review}

    def followups(state: AgentState) -> AgentState:
        today = state["today"]
        apps = tracker.all()
        stale = tracker.stale(today, state.get("stale_days", 10))
        drafts: dict[str, str] = {}
        review = list(state.get("review", []))
        for a in stale if llm else []:
            try:
                drafts[a.company] = draft_followup(llm, a, today)
            except Exception as exc:  # drafting is optional: report it, don't abort the run
                review.append(
                    {"email_id": f"followup:{a.company}", "reason": f"draft failed: {exc}"}
                )
        return {
            "due_soon": due_soon(apps, today),
            "stale": stale,
            "drafts": drafts,
            "review": review,
        }

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("apply", apply)
    graph.add_node("followups", followups)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        lambda s: "apply" if s.get("extractions") else "followups",
        {"apply": "apply", "followups": "followups"},
    )
    graph.add_edge("apply", "followups")
    graph.add_edge("followups", END)
    return graph.compile()


def run_agent(
    emails: list[Email],
    classifier: Classifier,
    tracker: Tracker,
    llm=None,
    today: date | None = None,
    stale_days: int = 10,
) -> AgentState:
    agent = build_agent(classifier, tracker, llm)
    return agent.invoke(
        {"emails": emails, "today": today or date.today(), "stale_days": stale_days}
    )


def main() -> None:
    from pathlib import Path

    from job_agent.classifier import LlmClassifier
    from job_agent.demo_data import load_emails
    from job_agent.llm import get_llm, get_llm_chain
    from job_agent.tracker import CsvTracker

    parser = argparse.ArgumentParser(description="Run the agent on the synthetic demo emails.")
    parser.add_argument("--today", type=date.fromisoformat, default=date(2026, 11, 20))
    parser.add_argument("--tracker", type=Path, default=Path("demo_output/tracker.csv"))
    args = parser.parse_args()

    tracker = CsvTracker(args.tracker)
    state = run_agent(
        load_emails(), LlmClassifier(get_llm_chain()), tracker, get_llm(), today=args.today
    )
    print(f"Tracker updated ({len(state['updated'])} changes) -> {args.tracker}")
    print(f"Ignored: {len(state['ignored'])} | Needs review: {len(state['review'])}")
    for item in state["review"]:
        print(f"  review {item['email_id']}: {item['reason']}")
    print("\nDue in the next 48 h:")
    for a in state["due_soon"]:
        print(f"  {a.company} / {a.role}: {a.status.value} on {a.due}")
    print(f"\nNo news for {10}+ days (drafts, not sent): {len(state['stale'])}")
    for company, text in state["drafts"].items():
        print(f"\n--- {company} ---\n{text}")


if __name__ == "__main__":
    main()
