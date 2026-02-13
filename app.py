import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import pandas as pd
import requests
import os
import datetime
import json
import time
import urllib.parse

# --- CONFIGURATION ---
DB_FILE = "csgo_api_v47.json"
STEAMDT_BASE_URL = "https://open.steamdt.com/open/cs2/v1/price/single"
USER_DATA_DIR = "user_data"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="JDL System", 
    page_icon="🏢", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- USER-SPECIFIC PATH FUNCTIONS ---
def get_user_folder(user_email):
    if not user_email: return None
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, mode=0o700)
    user_folder = os.path.join(USER_DATA_DIR, user_email.replace("@", "_at_").replace(".", "_dot_"))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, mode=0o700)
    return user_folder

def get_user_portfolio_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "portfolio.csv") if folder else None

def get_user_api_key_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "api_key.txt") if folder else None

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=300)

# Initialize Session State
for key, val in [("admin_verified", False), ("user_verified", False), 
                 ("user_email", None), ("user_name", None), ("api_key", "")]:
    if key not in st.session_state:
        st.session_state[key] = val

# --- CORE ENGINE FUNCTIONS ---
def load_api_key(user_email):
    path = get_user_api_key_path(user_email)
    if path and os.path.exists(path):
        with open(path, "r") as f: return f.read().strip()
    return ""

def save_api_key(user_email, key):
    path = get_user_api_key_path(user_email)
    if path:
        with open(path, "w") as f: f.write(key.strip())

@st.cache_data(ttl=3600)
def load_local_database():
    if not os.path.exists(DB_FILE): return None, "❌ Database Not Found"
    try:
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        items = data.get("items", [])
        return {item: {"name": item} for item in items}, None
    except Exception as e: return None, str(e)

def load_portfolio(user_email):
    cols = ["Item name", "Current price"]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            for c in cols:
                if c not in df.columns: df[c] = 0.0 if c == "Current price" else ""
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_portfolio(user_email, df):
    path = get_user_portfolio_path(user_email)
    if path: 
        df[["Item name", "Current price"]].to_csv(path, index=False, encoding="utf-8-sig")

def fetch_market_data(item_hash, api_key):
    try:
        encoded_name = urllib.parse.quote(item_hash)
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{STEAMDT_BASE_URL}?marketHashName={encoded_name}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            if not data: return None, "No data"
            price = next((m['sellPrice'] for m in data if m['platform'] == "BUFF"), data[0]['sellPrice'])
            return price, None
        return None, f"HTTP {r.status_code}"
    except Exception as e: return None, str(e)

# --- USER DASHBOARD ---
def user_dashboard():
    DB_DATA, _ = load_local_database()
    user_email = st.session_state.user_email
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(user_email)
    
    st.title("📟 JDL Terminal")
    df_raw = load_portfolio(user_email)
    
    t = st.tabs(["🛰️ Monitor", "🏠 Add Items", "⚙️ Management"])
    
    with t[0]:
        if not df_raw.empty:
            st.dataframe(df_raw, use_container_width=True, hide_index=True)
        else: st.info("Add items in the Homepage tab.")

    with t[1]:
        st.subheader("Add Items from Database")
        if DB_DATA:
            valid_items = sorted(list(DB_DATA.keys()))
            selected_item = st.selectbox("Select Item", [""] + valid_items)
            
            if st.button("✅ Add Item"):
                if not st.session_state.api_key:
                    st.error("Please set your SteamDT API Key in Management first.")
                elif selected_item and selected_item not in df_raw["Item name"].values:
                    price, err = fetch_market_data(selected_item, st.session_state.api_key)
                    if price:
                        new_row = pd.DataFrame([{"Item name": selected_item, "Current price": price}])
                        df_updated = pd.concat([df_raw, new_row], ignore_index=True)
                        save_portfolio(user_email, df_updated)
                        st.success(f"{selected_item} added!")
                        st.rerun()
                    else: st.error(f"Sync failed: {err}")
        else: st.error("Database file missing.")

    with t[2]:
        st.subheader("⚙️ API Configuration")
        api_input = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(user_email, api_input)
            st.session_state.api_key = api_input
            st.success("API Key saved.")

        st.divider()
        if st.button("🔄 Refresh Prices"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    price, _ = fetch_market_data(row['Item name'], st.session_state.api_key)
                    if price:
                        df_raw.at[idx, "Current price"] = price
                    p.progress((i + 1) / len(df_raw))
                    time.sleep(1.2)
                save_portfolio(user_email, df_raw)
                st.success("Prices refreshed!")
                st.rerun()

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    else: user_dashboard()

if __name__ == "__main__":
    main()