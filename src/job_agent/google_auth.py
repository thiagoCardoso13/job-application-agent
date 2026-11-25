"""OAuth for the Google APIs. Read-only Gmail plus Sheets; tokens stay on this machine."""

from __future__ import annotations

from pathlib import Path

GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
SHEETS = "https://www.googleapis.com/auth/spreadsheets"


def get_credentials(
    scopes: list[str],
    credentials_file: Path = Path("credentials.json"),
    token_file: Path = Path("token.json"),
):
    """Return valid user credentials, opening the browser consent flow the first time."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not credentials_file.exists():
            raise FileNotFoundError(
                f"{credentials_file} not found. Follow docs/SETUP.md to create it."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scopes)
        creds = flow.run_local_server(port=0)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(name: str, version: str, scopes: list[str]):
    from googleapiclient.discovery import build

    return build(name, version, credentials=get_credentials(scopes), cache_discovery=False)
