import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# If you change these scopes, delete token.json and re-authenticate
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
TOKEN_FILE = BASE_DIR / 'token.json'


def get_gmail_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None

    # Load existing token if it exists
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, run the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

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
