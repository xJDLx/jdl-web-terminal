import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import streamlit as st
from functools import lru_cache
import random

def init_google_sheets():
    """Initialize Google Sheets connection"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if not os.path.exists('google_sheets_credentials.json'):
            raise FileNotFoundError("Missing 'google_sheets_credentials.json'")
        
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_sheets_credentials.json', scope)
        return gspread.authorize(creds)
    except Exception as e:
        raise Exception(f"Setup Required: {str(e)}")

@lru_cache(maxsize=5)
def _cached_read_sheet(sheet_name, worksheet_name, cache_key):
    """Cached version of sheet reading to minimize API calls"""
    client = init_google_sheets()
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)
    return pd.DataFrame(worksheet.get_all_records())

def read_sheet_safe(sheet_name, worksheet_name):
    """Read data with exponential backoff for rate limit protection"""
    for i in range(5):  # Try 5 times
        try:
            # Key based on 5-minute window
            cache_key = datetime.now().strftime("%Y%m%d%H%M")[:-1]
            return _cached_read_sheet(sheet_name, worksheet_name, cache_key)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (2 ** i) + random.random()
                time.sleep(wait_time)
                continue
            raise e
    raise Exception("Max retries exceeded for Google Sheets API")

def update_sheet(sheet_name, worksheet_name, df):
    """Update Google Sheet with rate limiting"""
    try:
        # Enforce minimum 2-second interval between writes
        last_update = getattr(update_sheet, '_last_update', None)
        if last_update:
            diff = (datetime.now() - last_update).total_seconds()
            if diff < 2: time.sleep(2 - diff)
            
        client = init_google_sheets()
        worksheet = client.open(sheet_name).worksheet(worksheet_name)
        
        worksheet.clear()
        worksheet.update('A1', [df.columns.tolist()] + df.values.tolist())
            
        update_sheet._last_update = datetime.now()
        _cached_read_sheet.cache_clear()
    except Exception as e:
        raise Exception(f"Update Failed: {e}")