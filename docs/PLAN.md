# Job Application Agent: plan

Portfolio project #7. An AI agent that reads recruiter emails, classifies them, updates a tracking sheet and reminds me when to follow up. It uses my own job search as the use case.

**Hard rule: everything free.** No paid service, no card-required trial.

## Problem

After ~190 applications, replies are scattered across the inbox: interview invitations, take-home tests, rejections, automatic acknowledgements. Tracking them by hand is slow and things get missed.

## What the agent does

1. **Reads** new emails (Gmail API, read-only scope) or sample emails in demo mode.
2. **Classifies** each one: `interview`, `test`, `rejection`, `info_request`, `acknowledgement`, `other`.
3. **Extracts** company, role, deadline/date and the next action.
4. **Updates** the tracker (Google Sheets, or local CSV in demo mode).
5. **Flags follow-ups**: applications with no reply after N days, deadlines in the next 48 h.

## Stack (all free)

| Piece | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Same as the other projects |
| Agent | LangGraph + tool calling | Already used in the text-to-SQL project, but here with *side-effect tools* |
| LLM | Gemini free tier (`gemini-3.5-flash-lite`), Groq as optional fallback | Free and fast |
| Email | Gmail API (read-only OAuth) | Free quota is plenty |
| Tracker | Google Sheets API, CSV adapter for demo/tests | Same interface, two backends |
| UI | Streamlit (live demo on Streamlit Cloud) | Free hosting, demo mode with fake emails |
| Quality | pytest, ruff, GitHub Actions, small eval set of labelled emails | Same standard as projects #1 to #3 |

## Tools the agent can call

- `list_new_emails(since)`: returns unread messages (id, sender, subject, body).
- `classify_email(id)`: structured output (category, company, role, date, confidence).
- `upsert_application(company, role, status, next_action, due)`: writes to the tracker.
- `list_stale_applications(days)`: rows with no news after N days.
- `draft_followup(company)`: drafts a follow-up text (never sends it).

## Safety decisions

- **Read-only Gmail scope.** The agent never sends, deletes or labels emails.
- Follow-ups are only *drafted*, a human copies them.
- Low-confidence classifications go to a "needs review" status instead of overwriting the tracker.
- Real emails never reach the public demo: it only uses synthetic emails in `demo_data/`.
- No credentials in the repo (`.env`, `token.json` in `.gitignore`).

## Milestones

1. **Skeleton + demo data**: repo, CI, 30 synthetic labelled emails (EN/ES), CSV tracker.
2. **Classifier**: structured extraction + eval script (accuracy per category).
3. **Agent graph**: tools, review queue, follow-up logic, tests with a fake LLM.
4. **Gmail + Sheets adapters**: OAuth flow, documented setup.
5. **Streamlit UI**: inbox → classification → tracker view, tool timeline.
6. **Deploy + README**: live demo, GIF, architecture diagram, eval numbers, post text.

MVP (milestones 1 to 3 plus a minimal UI) fits in one day; the rest in the following days.

## How I'll show it

Live demo with synthetic emails, README with problem · solution · GIF · how to run · what I learned, an eval table, and one English LinkedIn post (see the posting order in the portfolio plan).

## Open questions

- Gemini free-tier rate limits when classifying batches: add batching and retry.
- Whether to also support Outlook (probably not for the MVP).
