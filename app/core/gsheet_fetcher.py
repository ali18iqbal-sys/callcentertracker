"""gsheet_fetcher.py - Google Sheet se data fetch"""

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


def extract_sheet_id(url):
    if "/d/" in url:
        return url.split("/d/")[1].split("/")[0]
    return url.strip()


def fetch_gsheet(url, credential_file, sheet_name=None):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(credential_file, scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet_id = extract_sheet_id(url)
    spreadsheet = client.open_by_key(sheet_id)
    
    if sheet_name and sheet_name.strip():
        worksheet = spreadsheet.worksheet(sheet_name.strip())
    else:
        worksheet = spreadsheet.sheet1
    
    data = worksheet.get_all_records()
    if not data:
        raise ValueError("Sheet khali hai")
    return pd.DataFrame(data)
