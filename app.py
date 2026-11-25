"""Streamlit demo: inbox -> classification -> tracker -> follow-ups (synthetic emails only)."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_agent.classifier import LlmClassifier  # noqa: E402
from job_agent.demo_data import load_emails  # noqa: E402
from job_agent.demo_session import DemoSession, LimitReached  # noqa: E402
from job_agent.followups import draft_followup, due_soon  # noqa: E402
from job_agent.replay import ReplayClassifier  # noqa: E402

DEMO_TODAY = date(2026, 11, 20)
MAX_LLM_CALLS = int(os.getenv("MAX_LLM_CALLS", "10"))

st.set_page_config(page_title="Job Application Agent", page_icon="📬", layout="wide")


def setting(name: str) -> str | None:
    if os.getenv(name):
        return os.getenv(name)
    try:
        return str(st.secrets[name]) if name in st.secrets else None
    except Exception:
        return None


@st.cache_data
def emails():
    return load_emails()


@st.cache_resource
def replay():
    return ReplayClassifier.load()


def init_state() -> None:
    if "session" not in st.session_state:
        st.session_state.session = DemoSession(DEMO_TODAY, MAX_LLM_CALLS)


def live_classifier():
    """Real model, limited per session to protect the free quota. Tests may inject one."""
    if "classifier_override" in st.session_state:
        return st.session_state.classifier_override
    if not setting("GOOGLE_API_KEY"):
        return None
    os.environ.setdefault("GOOGLE_API_KEY", setting("GOOGLE_API_KEY"))
    from job_agent.llm import get_llm_chain

    return LlmClassifier(get_llm_chain())


init_state()
sess: DemoSession = st.session_state.session
all_emails = emails()
by_id = {e.id: e for e in all_emails}
replay_clf = replay()
live = live_classifier()

st.title("📬 Job Application Agent")
st.caption(
    "An AI agent that reads recruiter emails, classifies them, updates a tracker and flags "
    "follow-ups. **All emails here are synthetic.** Nothing is sent anywhere."
)

with st.sidebar:
    st.subheader("Demo controls")
    st.write(f"Simulated date: **{DEMO_TODAY}**")
    st.write(f"Live AI calls: **{sess.llm_calls}/{MAX_LLM_CALLS}**")
    if replay_clf:
        if st.button("▶ Run the agent on all 30 emails", type="primary"):
            sess.run(all_emails, replay_clf, "saved real-model answers", metered=False)
            st.rerun()
        st.caption("Replays answers the real model already gave, so it costs no quota.")
    else:
        st.info("Saved answers not generated yet: classify emails one by one below.")
    if st.button("Reset demo"):
        st.session_state.pop("session", None)
        st.rerun()

inbox_tab, tracker_tab, followup_tab, review_tab, log_tab = st.tabs(
    ["Inbox", "Tracker", "Follow-ups", "Review queue", "Tool timeline"]
)

with inbox_tab:
    left, right = st.columns([3, 4])
    with left:
        frame = pd.DataFrame(
            [{"id": e.id, "received": e.received, "from": e.sender, "subject": e.subject}
             for e in all_emails]
        )
        pick = st.dataframe(
            frame, hide_index=True, on_select="rerun", selection_mode="single-row",
            use_container_width=True, height=420,
        )
    with right:
        rows = pick.selection.rows
        if not rows:
            st.info("Select an email on the left.")
        else:
            email = by_id[frame.iloc[rows[0]]["id"]]
            st.markdown(f"**{email.subject}**  \n`{email.sender}` · {email.received}")
            st.write(email.body)
            if live is None:
                st.warning("No Gemini key configured: live classification is unavailable.")
            elif st.button("🤖 Classify and update tracker", key=f"go-{email.id}"):
                sess.run([email], live, "Gemini", metered=True)
                st.rerun()

with tracker_tab:
    apps = sess.tracker.all()
    if not apps:
        st.info("The tracker is empty. Run the agent on some emails first.")
    else:
        table = pd.DataFrame([a.model_dump(mode="json") for a in apps])
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.bar_chart(table["status"].value_counts())

with followup_tab:
    apps = sess.tracker.all()
    soon = due_soon(apps, DEMO_TODAY)
    stale = sess.tracker.stale(DEMO_TODAY, 10)
    st.subheader("Due in the next 48 hours")
    st.dataframe(
        pd.DataFrame([a.model_dump(mode="json") for a in soon]) if soon else pd.DataFrame(),
        hide_index=True,
    )
    st.subheader("No news for 10+ days")
    for a in stale:
        with st.expander(f"{a.company} · {a.role} (last update {a.last_update})"):
            if a.company in sess.drafts:
                st.text(sess.drafts[a.company])
            elif live is not None and st.button("✍ Draft follow-up", key=f"d-{a.company}"):
                try:
                    sess.spend_call()
                except LimitReached as exc:
                    st.error(str(exc))
                else:
                    from job_agent.llm import get_llm

                    sess.drafts[a.company] = draft_followup(
                        st.session_state.get("draft_llm_override") or get_llm(), a, DEMO_TODAY
                    )
                    st.rerun()
    st.caption("Drafts are text only. The agent never sends email.")

with review_tab:
    if not sess.review:
        st.success("Nothing needs review.")
    for item in sess.review:
        st.warning(f"`{item['email_id']}`: {item['reason']}")

with log_tab:
    st.code("\n".join(sess.log) or "No steps yet.", language="text")
