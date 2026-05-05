import base64
import json
import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
TOKEN_FILE = BASE_DIR / 'token.json'


def _secret(key):
    """Return the value of *key* from os.environ, then st.secrets, or None."""
    value = os.environ.get(key)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def get_gmail_service():
    """Authenticate and return a Gmail API service instance.

    Credential sources (tried in order):
      1. GMAIL_TOKEN_B64 env var / st.secret  — base64-encoded pickle of token.json
      2. Local token.json file
      3. Interactive OAuth flow using GMAIL_CREDENTIALS_JSON or local credentials.json
    """
    creds = None

    # ── Load existing token ────────────────────────────────────────────────────
    token_b64 = _secret('GMAIL_TOKEN_B64')
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    elif TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    # ── Refresh if expired ────────────────────────────────────────────────────
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # ── Run OAuth flow if still no valid credentials ───────────────────────────
    if not creds or not creds.valid:
        creds_json = _secret('GMAIL_CREDENTIALS_JSON')
        if creds_json:
            flow = InstalledAppFlow.from_client_config(json.loads(creds_json), SCOPES)
        elif CREDENTIALS_FILE.exists():
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        else:
            raise FileNotFoundError(
                "No Gmail credentials found. "
                "Place credentials.json in the project root, or set "
                "GMAIL_CREDENTIALS_JSON + GMAIL_TOKEN_B64 in your environment / st.secrets."
            )
        creds = flow.run_local_server(port=0)

        # Persist token locally when possible (silently skip on read-only filesystems)
        try:
            with open(TOKEN_FILE, 'wb') as f:
                pickle.dump(creds, f)
        except OSError:
            pass

    return build('gmail', 'v1', credentials=creds)


def test_connection():
    """Quick test to verify Gmail API connection is working."""
    service = get_gmail_service()
    profile = service.users().getProfile(userId='me').execute()
    print(f"Connected to Gmail as: {profile['emailAddress']}")
    print(f"Total messages: {profile['messagesTotal']}")
    return service


if __name__ == '__main__':
    test_connection()
