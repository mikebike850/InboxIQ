import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'inboxiq.db'

client = Anthropic()

CATEGORIES = [
    'Job Application',
    'Recruiter',
    'Bill/Fee',
    'Event Ticket',
    'Subscription/Mailing List',
    'Needs Response',
    'Informational',
    'Other'
]

SYSTEM_PROMPT = """You are an email classifier for a job seeker's inbox.
Analyze the email and return ONLY a JSON object with no other text.

Categories:
- Job Application: confirmation of a job application submitted
- Recruiter: outreach from a recruiter or hiring manager
- Bill/Fee: invoice, payment due, or financial statement
- Event Ticket: ticket confirmation, event registration
- Subscription/Mailing List: newsletter, marketing, promotional
- Needs Response: personal or professional email requiring a reply
- Informational: receipts, notifications, updates requiring no action
- Other: anything that doesn't fit above

Return exactly this JSON structure:
{
  "category": "<one of the categories above>",
  "urgency": "<High|Medium|Low>",
  "company_name": "<extracted company name or null>",
  "role_title": "<extracted job title or null>",
  "application_date": "<YYYY-MM-DD or null>",
  "interview_date": "<YYYY-MM-DD or null>",
  "has_date_mention": <true|false>,
  "is_mailing_list": <true|false>,
  "reasoning": "<one sentence explanation>"
}"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def classify_email(sender, subject, snippet):
    """Send email to Claude API and return structured classification."""
    user_message = f"""Classify this email:

From: {sender}
Subject: {subject}
Preview: {snippet}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    result['raw_response'] = raw
    return result


def run_classifier(batch_size=50):
    """Classify all unprocessed emails in batches."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting classifier...")

    conn = get_db()

    # Fetch unprocessed emails
    rows = conn.execute('''
        SELECT e.id, e.sender, e.subject, e.snippet
        FROM emails e
        LEFT JOIN classifications c ON e.id = c.email_id
        WHERE c.email_id IS NULL
        LIMIT ?
    ''', (batch_size,)).fetchall()

    print(f"Emails to classify: {len(rows)}")

    success = 0
    errors = 0

    for i, row in enumerate(rows):
        try:
            result = classify_email(row['sender'], row['subject'], row['snippet'])

            conn.execute('''
                INSERT INTO classifications
                    (email_id, category, urgency, company_name, role_title,
                     application_date, interview_date, has_date_mention,
                     is_mailing_list, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['id'],
                result.get('category'),
                result.get('urgency'),
                result.get('company_name'),
                result.get('role_title'),
                result.get('application_date'),
                result.get('interview_date'),
                1 if result.get('has_date_mention') else 0,
                1 if result.get('is_mailing_list') else 0,
                result.get('raw_response')
            ))

            conn.commit()
            success += 1

            if (i + 1) % 10 == 0:
                print(f"  Classified {i + 1}/{len(rows)}...")

            # Rate limit protection
            time.sleep(0.3)

        except Exception as e:
            errors += 1
            print(f"  Error on {row['id']}: {e}")
            continue

    conn.close()
    print(f"Done. Success: {success} | Errors: {errors}")


if __name__ == '__main__':
    run_classifier(batch_size=50)
