# Automatic Job Applications

A local-first Python MVP for discovering, ranking, preparing, tracking, and safely
submitting job applications for Sanat Konda.

## What It Does

- Imports public postings from Greenhouse, Lever, and Ashby APIs.
- Accepts manual and email-alert imports.
- Deduplicates and stores jobs in SQLite.
- Scores hardware roles using Sanat's target titles and skills.
- Generates a factual cover-letter draft with OpenAI, or a local fallback when no API
  key is configured.
- Queues or submits only allowlisted, high-scoring applications with approved answers.
- Records state changes, filled fields, generated materials, receipts, and exceptions.
- Produces `outputs/daily_report_YYYY-MM-DD.md`.
- Provides FastAPI endpoints and a Streamlit review UI.

## What It Refuses To Automate

The agent does not scrape LinkedIn or Indeed and does not automate their application
flows. It does not bypass CAPTCHAs, login walls, rate limits, robots.txt, website access
controls, or anti-bot systems. A CAPTCHA always pauses that application for manual action.

Unknown legal, sensitive, consent, demographic, work-authorization, sponsorship,
clearance, salary, relocation, background-check, reference, government-ID, SSN, or
date-of-birth fields also pause the application unless the exact answer was explicitly
approved.

## Application States

`discovered`, `ranked`, `materials_generated`, `queued_for_submission`, `submitting`,
`submitted`, `special_case_waiting_for_user`, `user_replied`, `resumed`, `failed`,
`skipped`, and `archived`.

## Exception Emails

When an application cannot continue safely, the agent saves the job state and sends an
email with the company, title, URL, score, blocker, options, and recommended action.
Without Gmail credentials, it writes an `.eml` draft under `outputs/email_drafts/`.

Gmail replies are parsed by `parse_reply_instruction()`, attached to the job, and move
the job through `user_replied` to `resumed`. The MVP exposes these workflow functions;
the next production step is connecting reply polling to a durable portal-session
checkpoint.

## Windows Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest
uvicorn app.main:app --reload
streamlit run ui/streamlit_app.py
```

The original `..venv\Scripts\Activate.ps1` path in the specification points to a virtual
environment outside the repository. The command above creates and activates `.venv`
inside this repository.

## Configuration

1. Fill only explicitly approved values in `profile/preapproved_answers.yaml`.
2. Add reviewed public ATS boards to `profile/sources.yaml`.
3. Set `OPENAI_API_KEY` to enable model-generated materials.
4. Keep `AUTO_SUBMIT_ENABLED=false` during review and dry runs.
5. Add explicitly approved company hostnames to `ALLOWED_COMPANY_DOMAINS`.
6. Never put secrets or OAuth tokens in tracked files.

Source names `greenhouse`, `lever`, and `ashby` are platform-allowlisted, but live
submission still requires a supported adapter, no CAPTCHA/login blocker, complete
approved answers, and a score above the threshold.

## Gmail API

1. Create a Google Cloud project and enable the Gmail API.
2. Create an OAuth desktop-app credential.
3. Save the client-secret JSON outside Git-tracked paths.
4. Configure:

```dotenv
GMAIL_SENDER=your-address@gmail.com
GMAIL_RECIPIENT=sanat.konda4@gmail.com
GMAIL_CREDENTIALS_PATH=C:\secure\gmail_client_secret.json
GMAIL_TOKEN_PATH=C:\secure\gmail_token.json
EMAIL_POLL_INTERVAL_MINUTES=10
```

The first Gmail operation opens the OAuth consent flow and stores the token at the
configured path.

## Run the Scheduler

```powershell
python -m app.scheduler
```

The scheduler collects configured boards daily at 8:00 AM America/New_York and polls
Gmail replies at `EMAIL_POLL_INTERVAL_MINUTES`.

## Tests

```powershell
python -m pytest
```

Tests cover target-role scoring, low-value role scoring, LinkedIn/Indeed blocking,
sensitive and missing answers, exception emails, reply parsing, resumption, daily
reports, audit logging, allowlisting, and CAPTCHA stop behavior.

## Current MVP Limits

- Browser portal adapters and durable browser-session checkpoints are intentionally not
  implemented yet.
- Source board names must be configured before daily collection can fetch postings.
- Resumes and personal contact details still require manual setup.
