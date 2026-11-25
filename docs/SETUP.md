# Connect your own Gmail and Google Sheet

Everything here is free. You only need a Google account.

## 1. Create OAuth credentials (once)

1. Open <https://console.cloud.google.com/> and create a project (e.g. `job-agent`).
2. **APIs & Services → Library**: enable **Gmail API** and **Google Sheets API**.
3. **OAuth consent screen**: user type *External*, add yourself under *Test users*.
4. **Credentials → Create credentials → OAuth client ID → Desktop app**. Download the JSON
   and save it as `credentials.json` in the project root.

`credentials.json` and `token.json` are in `.gitignore`. Never commit them.

## 2. Create the sheet

Create an empty Google Sheet, rename the first tab to `Applications`, and copy the id from the
URL (`https://docs.google.com/spreadsheets/d/<THIS PART>/edit`). The agent writes the header row.

## 3. Run

```bash
PYTHONPATH=src python -m job_agent.agent --source gmail --sheet-id <SHEET_ID> --query "newer_than:14d"
```

The first run opens a browser to grant access.

## Privacy and safety

- Gmail scope is **read-only**: the agent cannot send, delete or label anything.
- The email text is sent to the Gemini API for classification. On the free tier, Google may use
  submitted content to improve its products, so **do not run it on emails you consider private**
  unless you accept that (use a narrower `--query`, or a paid/Ollama setup).
- Follow-ups are drafted and printed, never sent.
- Revoke access any time at <https://myaccount.google.com/permissions>.
