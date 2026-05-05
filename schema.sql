-- InboxIQ Database Schema
-- SQLite

-- Core email storage
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    sender TEXT,
    subject TEXT,
    snippet TEXT,
    body TEXT,
    timestamp INTEGER,
    labels TEXT,
    is_read INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Classification results from Claude API
CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL REFERENCES emails(id),
    category TEXT,
    urgency TEXT,
    company_name TEXT,
    role_title TEXT,
    application_date TEXT,
    interview_date TEXT,
    has_date_mention INTEGER DEFAULT 0,
    is_mailing_list INTEGER DEFAULT 0,
    raw_response TEXT,
    classified_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Job application tracking
CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    date_applied DATE,
    status TEXT DEFAULT 'Applied',
    thread_id TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Reminders and follow-ups
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT REFERENCES emails(id),
    job_application_id INTEGER REFERENCES job_applications(id),
    reminder_type TEXT,
    due_date DATETIME,
    delivered INTEGER DEFAULT 0,
    suppressed INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Subscription/mailing list tracking
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    domain TEXT,
    first_seen DATETIME,
    email_count INTEGER DEFAULT 1,
    unsubscribed INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);