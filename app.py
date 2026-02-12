import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import pandas as pd
import requests
import os
import datetime
import json
import time
import numpy as np
import urllib.parse

# --- CONFIGURATION ---
DB_FILE = "csgo_api_v47.json"
STEAMDT_BASE_URL = "https://open.steamdt.com/open/cs2/v1/price/single"
USER_DATA_DIR = "user_data"

# --- PAGE CONFIG ---
st.set_page_config(page_title="JDL System", layout="wide")

# --- CORE ENGINE FUNCTIONS ---
def fetch_market_data(item_hash, api_key):
    """Fetches Price, Supply, and Vol with specialized 404 handling for Agents"""
    try:
        # URL encode the name to handle the '|' character safely
        encoded_name = urllib.parse.quote(item_hash)
        headers = {"Authorization": f"Bearer {api_key}"}
        
        r = requests.get(f"{STEAMDT_BASE_URL}?marketHashName={encoded_name}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            res_json = r.json()
            data = res_json.get("data", [])
            if not data: return None, "Item Found but No Data"
            
            price = next((m['sellPrice'] for m in data if m['platform'] == "BUFF"), data[0]['sellPrice'])
            supply = sum(m.get("sellCount", 0) for m in data)
            vol = sum(m.get("sellCount24h", m.get("biddingCount", 0)) for m in data)
            return {"price": price, "supply": supply, "volume": vol}, None
            
        elif r.status_code == 404:
            return None, "404: Item Not Found (Check naming/spacing)"
        else:
            return None, f"Error {r.status_code}"
    except Exception as e:
        return None, f"Request Failed: {str(e)}"

# --- USER DASHBOARD SYNC LOGIC ---
def user_dashboard():
    # ... (rest of your dashboard code)
    if st.button("🔄 Global Sync"):
        if not st.session_state.api_key: st.error("Set API Key")
        else:
            df_raw = load_portfolio(st.session_state.user_email)
            p = st.progress(0)
            for i, (idx, row) in enumerate(df_raw.iterrows()):
                data, err = fetch_market_data(row['Item Name'], st.session_state.api_key)
                if data:
                    df_raw.at[idx, "Price (CNY)"] = data["price"]
                    df_raw.at[idx, "Supply"] = data["supply"]
                    df_raw.at[idx, "Daily Vol"] = data["volume"]
                else:
                    st.warning(f"Skipped {row['Item Name']}: {err}")
                p.progress((i + 1) / len(df_raw))
                time.sleep(1) # Safety delay
            save_portfolio(st.session_state.user_email, df_raw)
            st.success("Sync Process Finished")