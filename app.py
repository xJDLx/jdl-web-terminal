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

# --- CONFIGURATION ---
DB_FILE = "csgo_api_v47.json"
STEAMDT_BASE_URL = "https://open.steamdt.com/open/cs2/v1/price/single"
USER_DATA_DIR = "user_data"

# Default Weights for Strategy Tuner
DEFAULT_WEIGHTS = {'abs': 0.4, 'mom': 0.3, 'div': 0.3}

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="JDL System", 
    page_icon="🏢", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- DARK MODE CSS ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {background-color: #0e1117;}
    [data-testid="stHeader"] {background-color: #0e1117;}
    [data-testid="stSidebar"] {background-color: #262730;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 2px; background-color: #0e1117; padding-bottom: 0px;}
    .stTabs [data-baseweb="tab"] {height: 50px; background-color: #0e1117; color: #b2b2b2; border-radius: 4px 4px 0px 0px;}
    .stTabs [aria-selected="true"] {background-color: #1e1e1e; border-bottom: 2px solid #00ff41; color: #00ff41;}
    </style>
""", unsafe_allow_html=True)

# --- USER-SPECIFIC PATH FUNCTIONS ---
def get_user_folder(user_email):
    if not user_email: return None
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, mode=0o700)
    user_folder = os.path.join(USER_DATA_DIR, user_email.replace("@", "_at_").replace(".", "_dot_"))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, mode=0o700)
    st.session_state.user_folder = user_folder
    return user_folder

def get_user_portfolio_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "portfolio.csv") if folder else None

def get_user_history_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "history.csv") if folder else None

def get_user_api_key_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "api_key.txt") if folder else None

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=300)

for key, val in [("admin_verified", False), ("user_verified", False), 
                 ("user_email", None), ("user_name", None),
                 ("w_abs", DEFAULT_WEIGHTS['abs']), ("w_mom", DEFAULT_WEIGHTS['mom']), 
                 ("w_div", DEFAULT_WEIGHTS['div']), ("api_key", "")]:
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
        if isinstance(data, list):
            return { (item.get("name") or item.get("market_hash_name")): item for item in data }, None
        items = data.get("items", [])
        if items and isinstance(items[0], str):
            return {item: {"name": item} for item in items}, None
        return {(item.get("name") or item.get("market_hash_name")): item for item in items}, None
    except Exception as e: return None, str(e)

def load_portfolio(user_email):
    cols = ["Item Name", "Type", "AT Price", "AT Supply", "Price (CNY)", "Supply", "Daily Vol", "Last Updated"]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            for c in cols:
                if c not in df.columns: df[c] = 0
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_portfolio(user_email, df):
    path = get_user_portfolio_path(user_email)
    if path: df.to_csv(path, index=False, encoding="utf-8-sig")

def fetch_market_data(item_hash, api_key):
    """Fetches Price, Supply, and Daily Volume from SteamDT"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        r = requests.get(STEAMDT_BASE_URL, params={"marketHashName": item_hash}, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if not data: return None, "Not Found"
            
            # Prefer BUFF for price, sum sellCount for total supply
            price = next((m['sellPrice'] for m in data if m['platform'] == "BUFF"), data[0]['sellPrice'])
            supply = sum(m.get("sellCount", 0) for m in data)
            
            # Daily Volume is often represented as 24h sales or sell count in API snippets
            volume = sum(m.get("sellCount24h", 0) for m in data) 
            
            return {"price": price, "supply": supply, "volume": volume}, None
        return None, f"Error {r.status_code}"
    except: return None, "Request Failed"

# --- USER DASHBOARD ---
def user_dashboard():
    DB_DATA, DB_ERROR = load_local_database()
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(st.session_state.user_email)
    
    st.title("📟 JDL Intelligence Terminal")
    df_raw = load_portfolio(st.session_state.user_email)
    
    t = st.tabs(["🏠 Homepage", "🛰️ Predictor", "⚙️ Management"])
    
    with t[0]:
        st.subheader("Add New Item from Database")
        if DB_DATA:
            item_list = sorted(list(DB_DATA.keys()))
            selected_item = st.selectbox("Search Database:", [""] + item_list)
            if selected_item:
                if st.button("✅ Add to Portfolio"):
                    if selected_item in df_raw["Item Name"].values:
                        st.warning("Item already exists.")
                    else:
                        new_row = pd.DataFrame([{
                            "Item Name": selected_item,
                            "Type": DB_DATA[selected_item].get("type", "Unknown"),
                            "AT Price": 0, "AT Supply": 0, "Price (CNY)": 0, "Supply": 0, "Daily Vol": 0,
                            "Last Updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        }])
                        df_updated = pd.concat([df_raw, new_row], ignore_index=True)
                        save_portfolio(st.session_state.user_email, df_updated)
                        st.success("Added!")
                        st.rerun()

    with t[1]:
        if not df_raw.empty:
            st.dataframe(df_raw, use_container_width=True, hide_index=True)
        else: st.info("Add items in Homepage")

    with t[2]:
        new_key = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(st.session_state.user_email, new_key)
            st.session_state.api_key = new_key
            st.success("Saved!")
        
        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, err = fetch_market_data(row['Item Name'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Price (CNY)"] = data["price"]
                        df_raw.at[idx, "Supply"] = data["supply"]
                        df_raw.at[idx, "Daily Vol"] = data["volume"]
                        df_raw.at[idx, "Last Updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    p.progress((i + 1) / len(df_raw))
                    time.sleep(1.5) # Avoid rate limits
                save_portfolio(st.session_state.user_email, df_raw)
                st.success("Sync Complete")

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    elif st.session_state.admin_verified: pass # Admin logic here
    else: user_dashboard()

if __name__ == "__main__":
    main()