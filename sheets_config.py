import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def init_google_sheets():
    """Initialize Google Sheets connection"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('google_sheets_credentials.json', scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize Google Sheets: {e}")

def read_sheet(sheet_name, worksheet_name):
    """Read data from Google Sheet"""
    try:
        client = init_google_sheets()
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        raise Exception(f"Failed to read sheet: {e}")

def update_sheet(sheet_name, worksheet_name, df):
    """Update Google Sheet with DataFrame"""
    try:
        client = init_google_sheets()
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        
        # Get current data to check if update is needed
        try:
            current_data = worksheet.get_all_records()
            current_df = pd.DataFrame(current_data)
            if not df.empty and not current_df.empty:
                if df.equals(current_df):
                    return  # No update needed
        except:
            pass  # Continue with update if comparison fails
        
        # Clear existing content
        worksheet.clear()
        
        # Update headers
        headers = df.columns.tolist()
        worksheet.update('A1', [headers])
        
        # Update data
        if not df.empty:
            values = df.values.tolist()
            worksheet.update('A2', values)
            
    except Exception as e:
        raise Exception(f"Failed to update sheet: {e}")
