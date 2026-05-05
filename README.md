# InboxIQ

**AI-powered Gmail intelligence and job search dashboard**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?logo=streamlit&logoColor=white)
![Claude API](https://img.shields.io/badge/Claude-Sonnet_4.6-D97706?logo=anthropic&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Gmail API](https://img.shields.io/badge/Gmail-API-EA4335?logo=gmail&logoColor=white)
[![CI](https://github.com/mikebike850/inboxiq/actions/workflows/lint.yml/badge.svg)](https://github.com/mikebike850/inboxiq/actions/workflows/lint.yml)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://inboxiq-gfwp8whvtnxe9gnmrarzks.streamlit.app/)

InboxIQ connects to your Gmail inbox, classifies every email with Claude AI, and surfaces a six-tab dashboard purpose-built for active job seekers — track your pipeline, triage urgent replies, manage bills and event tickets, bulk-unsubscribe from noise, and visualize your search momentum, all from a single local app backed by SQLite.

---

## Screenshots

> Add screenshots to `docs/screenshots/` after your first run.

| Tab | What it shows |
|-----|---------------|
| **Respond Now** | Unread emails needing a reply, bucketed by AI-assigned urgency (High / Medium / Low) |
| **Job Pipeline** | 7-stage kanban board; inline status changes, one-click import from classified emails |
| **Bills & Tickets** | Bills ranked by urgency and due date; event tickets sorted by event date |
| **Application Search** | Live full-text + multi-filter search across all classified mail; "In Pipeline" badge |
| **KPI Dashboard** | Pipeline funnel, weekly applications timeline, inbox category breakdown |
| **Unsubscribe Queue** | All detected mailing lists in one place with persistent per-sender done tracking |

---

## Features

- **Local-first** — emails are stored in a local SQLite database; no data leaves your machine except the two API calls below
- **Claude AI classification** — each email is assigned a category, urgency, and extracted fields (company, role title, application date, interview date) via a single structured JSON call to `claude-sonnet-4-6`
- **Job Pipeline kanban** — 7 stages (Applied → Phone Screen → Technical → Interview → Offer → Rejected → Withdrawn); drag-free inline status updates
- **Smart inbox triage** — Respond Now surfaces only emails that need action, sorted by urgency so High-priority items appear first
- **Bills & Tickets** — due-date-aware bill queue and event timeline with Mark Paid / Mark Done actions that remove items from the default view
- **Application Search** — full-text search across subject, sender, snippet, company, and role with simultaneous category and urgency filters; no submit button needed
- **KPI Dashboard** — pipeline funnel chart, weekly applications timeline, inbox category breakdown, top recruiter companies bar chart, urgency distribution
- **Unsubscribe Queue** — every detected mailing list sender in one filterable list; writes to a `subscriptions` table so unsubscribe state persists across sessions
- **Reminders engine** — idempotent scan that generates four reminder types: follow-up, interview-prep, bill-due, and event-upcoming

---

## Architecture

```
┌─────────────────────────────── DATA PIPELINE ──────────────────────────────┐
│                                                                              │
│   Gmail API ──► ingest.py ─────────────────────────────► emails table      │
│                 (fetch + dedup,                                              │
│                  up to 500/run)                                              │
│                                                                              │
│   Anthropic API ◄── classifier.py ◄── emails table                         │
│                      (batch classify) ──────────────► classifications table │
│                                                                              │
│   reminders.py ────────────────────────────────────► reminders table        │
│   (scan & schedule, run manually or via cron)                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────── STREAMLIT DASHBOARD ────────────────────────────┐
│                              app.py                                          │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐                  │
│  │ Respond Now  │  │ Job Pipeline │  │ Bills & Tickets  │                  │
│  └──────────────┘  └──────────────┘  └──────────────────┘                  │
│  ┌──────────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ Application Search   │  │ KPI Dashboard   │  │ Unsubscribe Queue    │  │
│  └──────────────────────┘  └─────────────────┘  └──────────────────────┘  │
│                                                                              │
│  All views read from SQLite via views/db.py — no live API calls in the UI  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────── SQLite SCHEMA (inboxiq.db) ────────────────────────────┐
│  emails  ──────►  classifications                                            │
│  job_applications                                                            │
│  reminders  (linked to emails or job_applications)                          │
│  subscriptions                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

The dashboard reads exclusively from SQLite — browsing is instant and works offline after the initial ingest + classify run.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Dashboard | Streamlit 1.57 |
| AI classification | Anthropic Claude API — `claude-sonnet-4-6` |
| Database | SQLite 3 (Python built-in `sqlite3`) |
| Gmail integration | `google-api-python-client` 2.x, OAuth 2.0 read-only |
| Data wrangling | pandas 2.x |
| Charts | Streamlit native charts (Altair under the hood) |

---

## Project Structure

```
inboxiq/
├── app.py                    # Streamlit entry point and sidebar routing
├── ingest.py                 # Gmail fetch + deduplication pipeline
├── classifier.py             # Claude API batch classifier
├── reminders.py              # Reminder generator and public API
├── gmail_client.py           # Gmail OAuth 2.0 helper
├── schema.sql                # SQLite table definitions
├── requirements.txt          # Python dependencies (pip freeze)
├── .env                      # ANTHROPIC_API_KEY (git-ignored)
├── credentials.json          # Google OAuth client secrets (git-ignored)
├── token.json                # Cached OAuth token (git-ignored)
├── inboxiq.db                # SQLite database (git-ignored)
└── views/
    ├── db.py                 # Shared get_db() → sqlite3 connection
    ├── respond_now.py        # Respond Now tab
    ├── job_pipeline.py       # Job Pipeline tab
    ├── bills_tickets.py      # Bills & Tickets tab
    ├── app_search.py         # Application Search tab
    ├── kpi_dashboard.py      # KPI Dashboard tab
    └── unsubscribe_queue.py  # Unsubscribe Queue tab
```

---

## Setup

### Prerequisites

- Python 3.10 or later
- A Google account with Gmail
- An [Anthropic API key](https://console.anthropic.com/)

### 1 — Clone and create a virtual environment

```bash
git clone https://github.com/your-username/inboxiq.git
cd inboxiq
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
pip install streamlit          # installed separately; not in requirements.txt
```

### 3 — Add your Anthropic API key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4 — Set up Google OAuth

1. Open [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** for a *Desktop application*
3. Download the JSON and save it as `credentials.json` in the project root
4. Enable the **Gmail API** for your project under *Enabled APIs & Services*

### 5 — Initialize the database

```bash
python -c "
import sqlite3, pathlib
conn = sqlite3.connect('inboxiq.db')
conn.executescript(pathlib.Path('schema.sql').read_text())
conn.commit()
conn.close()
print('Database ready.')
"
```

---

## Usage

### Step 1 — Ingest emails

Fetches up to 500 inbox messages and stores them locally. Subsequent runs only pull new messages.

```bash
python ingest.py
```

### Step 2 — Classify with Claude

Sends each unclassified email to Claude in batches of 50. Writes category, urgency, and extracted job fields back to SQLite.

```bash
python classifier.py
```

> **Cost estimate:** roughly $0.01–0.05 per 100 emails depending on snippet length.

### Step 3 — Launch the dashboard

```bash
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). Use the **🔄 Refresh Data** button in the sidebar to clear the cache after a new ingest or classify run.

### Step 4 — (Optional) Generate reminders

```bash
python reminders.py
```

Scans for follow-up opportunities, upcoming interviews, due bills, and approaching events. Safe to run repeatedly — fully idempotent.

---

## Email Categories

| Category | Description |
|----------|-------------|
| `Job Application` | Confirmation of an application you submitted |
| `Recruiter` | Outreach from a recruiter or hiring manager |
| `Bill/Fee` | Invoice, payment due, or financial statement |
| `Event Ticket` | Ticket confirmation or event registration |
| `Subscription/Mailing List` | Newsletter, marketing, or promotional email |
| `Needs Response` | Personal or professional email requiring a reply |
| `Informational` | Receipts, notifications, updates — no action needed |
| `Other` | Anything that doesn't fit the above |

---

## Reminder Types

| Type | Trigger condition |
|------|-------------------|
| `follow_up` | Application stuck in "Applied" for 7+ days with no status update |
| `interview_prep` | `interview_date` extracted from email is within the next 3 days |
| `bill_due` | High-urgency Bill/Fee email received in the last 7 days |
| `event_upcoming` | Event Ticket with a date in the next 7 days |

Use the public API from your own scripts:

```python
from reminders import get_pending_reminders, dismiss_reminder, deliver_reminder

for r in get_pending_reminders():
    print(r['reminder_type'], r['due_date'], r.get('app_company') or r.get('email_subject'))
```

---

## Deploying to Streamlit Community Cloud

The dashboard reads exclusively from `inboxiq.db` — no API keys are needed at runtime. The ingestion and classification steps run locally; only the resulting database is needed for the live app.

### Option A — Portfolio / demo (empty state)

Deploy without a database. Every tab shows a "No data yet" message. Useful for showcasing the code structure without publishing personal email data.

1. Fork the repo (or use your own)
2. Push to GitHub
3. Sign in to [share.streamlit.io](https://share.streamlit.io) → **New app** → select your repo, branch `main`, file `app.py`
4. Deploy — the app loads immediately. No secrets required.

### Option B — Live personal dashboard (real data)

Run the pipeline locally, then commit the database to a **private** repo so Streamlit Cloud can serve it.

```bash
# 1. Populate the database locally
python ingest.py
python classifier.py

# 2. Allow inboxiq.db to be committed (private repo only)
#    Remove the *.db line from .gitignore, then:
git add inboxiq.db
git commit -m "chore: add populated database"
git push origin main
```

The live app refreshes automatically on each push. To pull in new emails: run `ingest.py` + `classifier.py` locally and push again.

### Option C — Full cloud operation (credentials in secrets)

If you want to run ingestion from a cloud environment (e.g. a scheduled GitHub Action) rather than locally, store your Gmail credentials in Streamlit secrets:

1. Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` and fill in values
2. In the Streamlit Cloud dashboard: **App settings → Secrets** → paste the same key-value pairs
3. Generate `GMAIL_TOKEN_B64` after your first local OAuth flow:
   ```bash
   python -c "import base64; print(base64.b64encode(open('token.json','rb').read()).decode())"
   ```
4. `ANTHROPIC_API_KEY` is read from secrets automatically when `classifier.py` is invoked

### Secrets reference

| Secret | Required for | Where to get it |
|--------|-------------|-----------------|
| `ANTHROPIC_API_KEY` | Running `classifier.py` | [console.anthropic.com](https://console.anthropic.com) |
| `GMAIL_CREDENTIALS_JSON` | Running `ingest.py` without local file | Google Cloud Console → Credentials |
| `GMAIL_TOKEN_B64` | Non-interactive Gmail auth | Generated locally after first OAuth flow |
| `INBOXIQ_DB_PATH` | Custom database location | Optional override — default is project root |

---

## Privacy

All email data is stored locally in `inboxiq.db`. The only outbound API calls are:

| Call | What is sent |
|------|-------------|
| Gmail API | OAuth token to fetch your own emails |
| Anthropic API | Email subject, sender, and snippet — **not** the full email body |

`credentials.json`, `token.json`, and `*.db` are excluded from version control via `.gitignore`.
