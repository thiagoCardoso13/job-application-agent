# Job Application Agent

An AI agent that reads recruiter emails, classifies them (interview, test, rejection, info request, acknowledgement), updates a tracking sheet and flags follow-ups.

> Work in progress. See [docs/PLAN.md](docs/PLAN.md) for the plan and milestones.

## Status

- [x] Milestone 1: skeleton, 30 synthetic labelled emails (EN/ES), CSV tracker, CI
- [x] Milestone 2: Gemini classifier (structured output, model fallbacks) + eval: 100% on the synthetic set vs 63% for a keyword baseline, see [docs/eval.md](docs/eval.md)
- [x] Milestone 3: agent graph (LangGraph: classify → apply → follow-ups), review queue, status never goes backwards, follow-up drafts (never sent)
- [x] Milestone 4: read-only Gmail source + Google Sheets tracker (tested with fakes; the real OAuth flow is not exercised yet), see [docs/SETUP.md](docs/SETUP.md)
- [x] Milestone 5: Streamlit UI (inbox, tracker, follow-ups, review queue, tool timeline, per-session AI-call limit)
- [ ] Milestone 6: deploy

## Run the tests

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && pytest -q
```

All demo emails are synthetic (`demo_data/emails.json`); no real personal data is in this repo.

## Run the eval

```bash
cp .env.example .env   # add your free Google AI Studio key
PYTHONPATH=src python -m job_agent.evaluate --baseline --out docs/eval.md
```

## Run the agent on the demo emails

```bash
PYTHONPATH=src python -m job_agent.agent --today 2026-11-20
```

It writes `demo_output/tracker.csv`, lists deadlines in the next 48 h, applications with no news for 10+ days (with drafted follow-ups) and the emails that need human review.

## Run the web demo

```bash
streamlit run app.py
```

- With `demo_data/precomputed.json` present (generated once by `PYTHONPATH=src python scripts/precompute.py`), the sidebar button replays real model answers for all 30 emails at no cost.
- With a `GOOGLE_API_KEY`, you can also classify single emails live (limited per session by `MAX_LLM_CALLS`, default 10, to protect the free quota).
