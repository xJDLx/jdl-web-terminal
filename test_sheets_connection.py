#!/usr/bin/env python3
"""Test Google Sheets connection"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import toml

# Load secrets
try:
    with open('.streamlit/secrets.toml') as f:
        secrets = toml.load(f)
except Exception as e:
    print(f"Error loading secrets.toml: {e}")
    exit(1)

# Extract credentials
try:
    creds_dict = {k: v for k, v in secrets['connections']['gsheets'].items() if k != 'spreadsheet'}
    creds_dict['type'] = 'service_account'
    sheet_id = secrets['connections']['gsheets']['spreadsheet']
except Exception as e:
    print(f"Error parsing credentials: {e}")
    exit(1)

# Test connection
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    print(f"✓ Service account authenticated: {creds_dict.get('client_email')}")
    print(f"✓ Attempting to access spreadsheet ID: {sheet_id}")
    
    sheet = client.open_by_key(sheet_id)
    print(f"✓ Successfully opened: {sheet.title}")
    print(f"✓ Available worksheets: {[w.title for w in sheet.worksheets()]}")
    print("\n✓ Your Google Sheets connection is working correctly!")
    
except gspread.exceptions.SpreadsheetNotFound:
    print(f"✗ Spreadsheet not found with ID: {sheet_id}")
    print("\nFix: Verify the spreadsheet ID in .streamlit/secrets.toml exists")
    
except gspread.exceptions.APIError as e:
    if "Permission denied" in str(e):
        print(f"✗ Permission denied - Service account doesn't have access")
        print(f"\nFix: Share the Google Sheet with: {creds_dict.get('client_email')}")
        print("and grant 'Editor' access")
    else:
        print(f"✗ API Error: {e}")
        
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {str(e)}")
