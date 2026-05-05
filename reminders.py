import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / 'inboxiq.db'

FOLLOW_UP_DAYS = 7    # flag "Applied" jobs with no update after this many days
INTERVIEW_WINDOW = 3  # days ahead to create interview-prep reminders
BILL_LOOKBACK = 7     # days back to scan for high-urgency bills
EVENT_WINDOW = 7      # days ahead to create event reminders


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _reminder_exists(conn, reminder_type, *, email_id=None, job_application_id=None):
    if email_id:
        return conn.execute('''
            SELECT 1 FROM reminders
            WHERE reminder_type = ? AND email_id = ?
              AND delivered = 0 AND suppressed = 0
        ''', (reminder_type, email_id)).fetchone() is not None

    if job_application_id:
        return conn.execute('''
            SELECT 1 FROM reminders
            WHERE reminder_type = ? AND job_application_id = ?
              AND delivered = 0 AND suppressed = 0
        ''', (reminder_type, job_application_id)).fetchone() is not None

    return False


def _insert(conn, reminder_type, due_date, *, email_id=None, job_application_id=None):
    conn.execute('''
        INSERT INTO reminders (email_id, job_application_id, reminder_type, due_date)
        VALUES (?, ?, ?, ?)
    ''', (email_id, job_application_id, reminder_type, due_date))


# ── Generators ────────────────────────────────────────────────────────────────

def _follow_up_reminders(conn):
    """Applications stuck in 'Applied' for FOLLOW_UP_DAYS with no reminder yet."""
    cutoff = (datetime.now() - timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    apps = conn.execute('''
        SELECT id, company, role
        FROM job_applications
        WHERE status = 'Applied' AND updated_at < ?
    ''', (cutoff,)).fetchall()

    count = 0
    due = (datetime.now() + timedelta(days=1)).date().isoformat()
    for app in apps:
        if not _reminder_exists(conn, 'follow_up', job_application_id=app['id']):
            _insert(conn, 'follow_up', due, job_application_id=app['id'])
            print(f"  [follow_up]       {app['role']} @ {app['company']}")
            count += 1
    return count


def _interview_reminders(conn):
    """Interviews in the next INTERVIEW_WINDOW days."""
    today = datetime.now().date().isoformat()
    horizon = (datetime.now() + timedelta(days=INTERVIEW_WINDOW)).date().isoformat()

    rows = conn.execute('''
        SELECT email_id, interview_date, company_name, role_title
        FROM classifications
        WHERE interview_date IS NOT NULL
          AND interview_date >= ? AND interview_date <= ?
    ''', (today, horizon)).fetchall()

    count = 0
    for row in rows:
        if not _reminder_exists(conn, 'interview_prep', email_id=row['email_id']):
            _insert(conn, 'interview_prep', row['interview_date'], email_id=row['email_id'])
            print(f"  [interview_prep]  {row['role_title']} @ {row['company_name']} on {row['interview_date']}")
            count += 1
    return count


def _bill_reminders(conn):
    """High-urgency bills received within BILL_LOOKBACK days."""
    since = (datetime.now() - timedelta(days=BILL_LOOKBACK)).timestamp()

    rows = conn.execute('''
        SELECT c.email_id, c.company_name, c.application_date, e.subject
        FROM classifications c
        JOIN emails e ON c.email_id = e.id
        WHERE c.category = 'Bill/Fee'
          AND c.urgency = 'High'
          AND e.timestamp >= ?
    ''', (since,)).fetchall()

    count = 0
    for row in rows:
        if not _reminder_exists(conn, 'bill_due', email_id=row['email_id']):
            due = row['application_date'] or datetime.now().date().isoformat()
            _insert(conn, 'bill_due', due, email_id=row['email_id'])
            print(f"  [bill_due]        {row['subject']}")
            count += 1
    return count


def _event_reminders(conn):
    """Event tickets with a date in the next EVENT_WINDOW days."""
    today = datetime.now().date().isoformat()
    horizon = (datetime.now() + timedelta(days=EVENT_WINDOW)).date().isoformat()

    rows = conn.execute('''
        SELECT email_id, company_name, role_title,
               COALESCE(interview_date, application_date) AS event_date
        FROM classifications
        WHERE category = 'Event Ticket'
          AND COALESCE(interview_date, application_date) IS NOT NULL
          AND COALESCE(interview_date, application_date) >= ?
          AND COALESCE(interview_date, application_date) <= ?
    ''', (today, horizon)).fetchall()

    count = 0
    for row in rows:
        if not _reminder_exists(conn, 'event_upcoming', email_id=row['email_id']):
            _insert(conn, 'event_upcoming', row['event_date'], email_id=row['email_id'])
            print(f"  [event_upcoming]  {row['role_title'] or '(event)'} on {row['event_date']}")
            count += 1
    return count


# ── Public API ────────────────────────────────────────────────────────────────

def generate_reminders():
    """Scan for all reminder conditions and insert new records. Idempotent."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating reminders...")
    conn = get_db()

    total  = _follow_up_reminders(conn)
    total += _interview_reminders(conn)
    total += _bill_reminders(conn)
    total += _event_reminders(conn)

    conn.commit()
    conn.close()
    print(f"Done. {total} new reminder(s) created.")
    return total


def get_pending_reminders():
    """Return all undelivered, unsuppressed reminders with joined context."""
    conn = get_db()
    rows = conn.execute('''
        SELECT
            r.id, r.reminder_type, r.due_date, r.created_at,
            r.email_id, r.job_application_id,
            e.subject    AS email_subject,
            e.sender     AS email_sender,
            ja.company   AS app_company,
            ja.role      AS app_role,
            ja.status    AS app_status
        FROM reminders r
        LEFT JOIN emails e            ON r.email_id = e.id
        LEFT JOIN job_applications ja ON r.job_application_id = ja.id
        WHERE r.delivered = 0 AND r.suppressed = 0
        ORDER BY r.due_date ASC NULLS LAST
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dismiss_reminder(reminder_id):
    """Suppress a reminder — user has seen and dismissed it."""
    conn = get_db()
    conn.execute('UPDATE reminders SET suppressed = 1 WHERE id = ?', (reminder_id,))
    conn.commit()
    conn.close()


def deliver_reminder(reminder_id):
    """Mark a reminder as delivered (shown/acted on)."""
    conn = get_db()
    conn.execute('UPDATE reminders SET delivered = 1 WHERE id = ?', (reminder_id,))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    generate_reminders()
