import sqlite3
import base64
import email
import re
from datetime import datetime
from pathlib import Path
from gmail_client import get_gmail_service

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'inboxiq.db'


def get_db():
    """Return a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_already_processed_ids(conn):
    """Return set of message IDs already in the database."""
    cursor = conn.execute("SELECT id FROM emails")
    return {row['id'] for row in cursor.fetchall()}


def parse_message(msg):
    """Extract fields from a raw Gmail API message."""
    payload = msg.get('payload', {})
    headers = {h['name'].lower(): h['value']
               for h in payload.get('headers', [])}

    sender = headers.get('from', '')
    subject = headers.get('subject', '')
    timestamp = int(msg.get('internalDate', 0)) // 1000

    # Extract body text
    body = extract_body(payload)

    return {
        'id': msg['id'],
        'thread_id': msg.get('threadId', ''),
        'sender': sender,
        'subject': subject,
        'snippet': msg.get('snippet', ''),
        'body': body[:5000] if body else '',  # cap at 5000 chars
        'timestamp': timestamp,
        'labels': ','.join(msg.get('labelIds', [])),
        'is_read': 0 if 'UNREAD' in msg.get('labelIds', []) else 1,
        'processed': 0
    }


def extract_body(payload):
    """Recursively extract plain text body from Gmail payload."""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    for part in payload.get('parts', []):
        result = extract_body(part)
        if result:
            return result

    return ''


def insert_email(conn, email_data):
    """Insert a single email record into SQLite."""
    conn.execute('''
        INSERT OR IGNORE INTO emails
            (id, thread_id, sender, subject, snippet, body,
             timestamp, labels, is_read, processed)
        VALUES
            (:id, :thread_id, :sender, :subject, :snippet, :body,
             :timestamp, :labels, :is_read, :processed)
    ''', email_data)


def fetch_and_store(max_results=500):
    """Main ingestion function — fetch emails from Gmail and store in SQLite."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting ingestion...")

    service = get_gmail_service()
    conn = get_db()
    already_processed = get_already_processed_ids(conn)

    print(f"Already in DB: {len(already_processed)} messages")

    # Fetch list of message IDs from Gmail
    response = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        labelIds=['INBOX']
    ).execute()

    messages = response.get('messages', [])
    print(f"Found {len(messages)} messages in Gmail inbox")

    new_count = 0
    skip_count = 0

    for msg_ref in messages:
        msg_id = msg_ref['id']

        if msg_id in already_processed:
            skip_count += 1
            continue

        # Fetch full message
        msg = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        email_data = parse_message(msg)
        insert_email(conn, email_data)
        new_count += 1

        if new_count % 50 == 0:
            conn.commit()
            print(f"  Inserted {new_count} new emails...")

    conn.commit()
    conn.close()

    print(f"Done. New: {new_count} | Skipped (already in DB): {skip_count}")
    return new_count


if __name__ == '__main__':
    fetch_and_store(max_results=500)