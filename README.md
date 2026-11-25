# Job Application Agent

An AI agent that reads recruiter emails, classifies them (interview, test, rejection, info request, acknowledgement), updates a tracking sheet and flags follow-ups.

> Work in progress. See [docs/PLAN.md](docs/PLAN.md) for the plan and milestones.

## Status

- [x] Milestone 1: skeleton, 30 synthetic labelled emails (EN/ES), CSV tracker, CI
- [x] Milestone 2: Gemini classifier (structured output, model fallbacks) + eval: 100% on the synthetic set vs 63% for a keyword baseline, see [docs/eval.md](docs/eval.md)
- [ ] Milestone 3: agent graph
- [ ] Milestone 4: Gmail + Sheets adapters
- [ ] Milestone 5: Streamlit UI
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
