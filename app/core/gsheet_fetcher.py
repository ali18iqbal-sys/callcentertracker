"""
gsheet_fetcher.py — Data fetcher for Google Sheets.

The service-account key path is resolved through app.utils.secrets, so
credentials do not need to be configured in the source registry.
"""

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from app.utils.secrets import get_google_credentials_file

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def extract_sheet_id(url):
    """Extract the spreadsheet ID from a Google Sheets URL."""
    if "/d/" in url:
        return url.split("/d/")[1].split("/")[0]
    return url.strip()


def fetch_gsheet(url, credential_file=None, sheet_name=None):
    """Fetch a Google Sheet into a DataFrame.

    Args:
        url: spreadsheet URL (or bare sheet ID)
        credential_file: service-account JSON path; falls back to
            ``GOOGLE_APPLICATION_CREDENTIALS`` or Streamlit Secrets
        sheet_name: worksheet name; the first sheet is used when omitted

    Raises:
        FileNotFoundError: when the credentials file cannot be found
        ValueError: when the selected sheet contains no records
    """
    credential_file = get_google_credentials_file(credential_file)
    creds = Credentials.from_service_account_file(credential_file, scopes=SCOPES)
    client = gspread.authorize(creds)

    sheet_id = extract_sheet_id(url)
    spreadsheet = client.open_by_key(sheet_id)

    if sheet_name and sheet_name.strip():
        worksheet = spreadsheet.worksheet(sheet_name.strip())
    else:
        worksheet = spreadsheet.sheet1

    data = worksheet.get_all_records()
    if not data:
        raise ValueError("The selected sheet is empty.")
    return pd.DataFrame(data)