import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from functools import lru_cache

def init_google_sheets():
    """Initialize Google Sheets connection"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    try:
        if not os.path.exists('google_sheets_credentials.json'):
            raise FileNotFoundError(
                "\n1. Go to Google Cloud Console\n"
                "2. Create a project and enable Google Sheets API\n"
                "3. Create service account credentials\n"
                "4. Download JSON key file\n"
                "5. Save as 'google_sheets_credentials.json' in project root"
            )
        
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_sheets_credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Test connection by trying to open the sheet
        try:
            client.open("CSGO_Database")
        except gspread.SpreadsheetNotFound:
            raise Exception(
                "\n1. Create a Google Sheet named 'CSGO_Database'\n"
                "2. Share it with the email from your credentials file"
            )
            
        return client
    except Exception as e:
        raise Exception(f"Google Sheets Setup Required:\n{str(e)}")

@lru_cache(maxsize=1)
def _cached_read_sheet(sheet_name, worksheet_name, cache_key):
    """Cached version of sheet reading"""
    client = init_google_sheets()
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def read_sheet(sheet_name, worksheet_name):
    """Read data from Google Sheet with caching"""
    try:
        # Generate cache key based on 5-minute intervals
        cache_key = datetime.now().strftime("%Y%m%d%H%M")[:-1]
        
        # Use cached data if available and less than 5 minutes old
        return _cached_read_sheet(sheet_name, worksheet_name, cache_key)
    except Exception as e:
        raise Exception(f"Failed to read sheet: {e}")

def update_sheet(sheet_name, worksheet_name, df):
    """Update Google Sheet with DataFrame"""
    try:
        # Rate limiting based on last update time
        last_update = getattr(update_sheet, '_last_update', None)
        if last_update:
            time_since_update = (datetime.now() - last_update).total_seconds()
            if time_since_update < 2:  # Minimum 2 seconds between updates
                time.sleep(2 - time_since_update)
        client = init_google_sheets()
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        
        
        # Clear existing content
        worksheet.clear()
        
        # Update headers
        headers = df.columns.tolist()
        worksheet.update('A1', [headers])
        
        # Update data
        if not df.empty:
            values = df.values.tolist()
            worksheet.update('A2', values)
            
        # Store last update time
        update_sheet._last_update = datetime.now()
        # Clear the read cache to ensure fresh data on next read
        _cached_read_sheet.cache_clear()
            
    except Exception as e:
        raise Exception(f"Failed to update sheet: {e}")
