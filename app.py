import streamlit as st
import pandas as pd
import requests
import os
import datetime
import json
import time
import urllib.parse
import numpy as np

# --- CONFIGURATION ---
CSV_FILE = "portfolio.csv"
DB_FILE = "csgo_api_v47.json"
CONFIG_FILE = "api_key.txt"
STEAMDT_BASE_URL = "https://open.steamdt.com/open/cs2/v1/price/single"

def load_api_key():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return f.read().strip()
    return ""

def save_api_key(key):
    with open(CONFIG_FILE, "w") as f: f.write(key.strip())

@st.cache_data(ttl=3600)
def load_local_database():
    if not os.path.exists(DB_FILE): return None, "❌ Database Not Found"
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return { (item.get("name") or item.get("market_hash_name")): item for item in data }, None
        return data, None
    except Exception as e: return None, str(e)

def load_portfolio():
    # Updated required columns to prevent "nothing there" errors
    required = ["Item Name", "Type", "AT Price", "AT Supply", "Sess Price", "Sess Supply", "Price (CNY)", "Supply", "Last Updated"]
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        for col in required:
            if col not in df.columns: df[col] = 0
        return df[required]
    return pd.DataFrame(columns=required)

def save_portfolio(df):
    df.to_csv(CSV_FILE, index=False)

def fetch_market_data(item_hash, api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"marketHashName": item_hash}
        r = requests.get(STEAMDT_BASE_URL, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            item_meta = res.get("item", {})
            if not data: return None, "Not Found"
            price = next((m['sellPrice'] for m in data if m['platform'] == "BUFF"), data[0]['sellPrice'])
            supply = item_meta.get('quantity', sum(m.get("sellCount", 0) for m in data))
            return {"price": price, "supply": supply, "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}, None
        return None, f"Error {r.status_code}"
    except: return None, "Request Failed"

st.set_page_config(page_title="JDL Terminal Pro", layout="wide")
if "api_key" not in st.session_state: st.session_state.api_key = load_api_key()

DB_DATA, DB_ERROR = load_local_database()
st.title("📟 JDL Intelligence Terminal")
df_raw = load_portfolio()

# Add Item Logic
if DB_DATA:
    selected_item = st.selectbox("Select Item", options=[""] + list(DB_DATA.keys()))
    if st.button("Add Item"):
        if selected_item:
            init, err = fetch_market_data(selected_item, st.session_state.api_key)
            if init:
                new_row = {
                    "Item Name": selected_item, "Type": "Watchlist", 
                    "AT Price": init["price"], "AT Supply": init["supply"], 
                    "Sess Price": init["price"], "Sess Supply": init["supply"], 
                    "Price (CNY)": init["price"], "Supply": init["supply"], 
                    "Last Updated": init["updated"]
                }
                df_raw = pd.concat([df_raw, pd.DataFrame([new_row])], ignore_index=True)
                save_portfolio(df_raw)
                st.rerun()