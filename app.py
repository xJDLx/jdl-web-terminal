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
DEFAULT_WEIGHTS = {'abs': 0.4, 'mom': 0.3, 'div': 0.3}

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

def get_user_history_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "history.csv") if folder else None

def get_user_api_key_path(user_email):
    folder = get_user_folder(user_email)
    return os.path.join(folder, "api_key.txt") if folder else None

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=300)

# Initialize Session State
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
    """Loads the valid item list from csgo_api_v47.json"""
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
    cols = ["Name of", "Entry price", "Entry supply", "Current price", "current supply", 
            "supply change number(%)", "price change number(%)", "Entry date", "Score", "Reason", "Daily sales"]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            for c in cols:
                if c not in df.columns: 
                    df[c] = 0 if "(%)" not in c else 0.0
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_portfolio(user_email, df):
    path = get_user_portfolio_path(user_email)
    if path: 
        save_cols = ["Name of", "Entry price", "Entry supply", "Current price", "current supply", 
                     "supply change number(%)", "price change number(%)", "Entry date", "Score", "Reason", "Daily sales"]
        df[save_cols].to_csv(path, index=False, encoding="utf-8-sig")

def load_history(user_email):
    path = get_user_history_path(user_email)
    if path and os.path.exists(path):
        try: 
            df = pd.read_csv(path, encoding="utf-8-sig")
            df['Date'] = pd.to_datetime(df['Date'])
            return df
        except: pass
    return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply"])

def save_history_entry(user_email, item_name, price, supply):
    df_hist = load_history(user_email)
    new_entry = pd.DataFrame([{
        "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "Item Name": item_name, "Price (CNY)": price, "Supply": supply
    }])
    updated = pd.concat([df_hist, new_entry], ignore_index=True)
    path = get_user_history_path(user_email)
    if path: updated.to_csv(path, index=False, encoding="utf-8-sig")

def get_bought_momentum(user_email, item_name):
    df_h = load_history(user_email)
    if df_h.empty: return 0, 0, 0
    item_data = df_h[df_h["Item Name"] == item_name].sort_values("Date")
    if len(item_data) < 2: return 0, 0, 0
    
    item_data['buys'] = (item_data['Supply'].shift(1) - item_data['Supply']).clip(lower=0)
    now = datetime.datetime.now()
    t_3h, t_24 = now - datetime.timedelta(hours=3), now - datetime.timedelta(hours=24)
    
    b_3h = item_data[item_data["Date"] >= t_3h]['buys'].sum()
    b_today = item_data[item_data["Date"] >= t_24.replace(hour=0, minute=0)]['buys'].sum()
    y_start = (t_24 - datetime.timedelta(days=1)).replace(hour=0, minute=0)
    b_yesterday = item_data[(item_data["Date"] >= y_start) & (item_data["Date"] < t_24.replace(hour=0, minute=0))]['buys'].sum()
    
    return int(b_3h), int(b_today), int(b_yesterday)

def calculate_metrics(user_email, row, weights):
    e_price, e_supply = row["Entry price"], row["Entry supply"]
    c_price, c_supply = row["Current price"], row["current supply"]
    
    supply_change = ((e_supply - c_supply) / max(1, e_supply)) * 100
    price_change = ((c_price - e_price) / max(0.01, e_price)) * 100
    
    b_3h, b_today, b_yest = get_bought_momentum(user_email, row['Name of'])
    
    abs_pts = np.clip(supply_change * 10, 0, 100)
    mom_pts = 100 if b_today > b_yest and b_today > 0 else (50 if b_3h > 0 else 0)
    
    total_score = round((abs_pts * weights['abs']) + (mom_pts * weights['mom']), 1)
    status = "🥇 THE BEST" if total_score >= 80 else ("❌ THE WORST" if total_score < 15 else "⚖️ NEUTRAL")
    
    return pd.Series({
        "supply change number(%)": round(supply_change, 2),
        "price change number(%)": round(price_change, 2),
        "Score": total_score,
        "Reason": status,
        "Daily sales": b_today
    })

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
            supply = sum(m.get("sellCount", 0) for m in data)
            return {"price": price, "supply": supply}, None
        return None, f"API {r.status_code}"
    except Exception as e: return None, str(e)

# --- USER DASHBOARD ---
def user_dashboard():
    DB_DATA, DB_ERROR = load_local_database()
    user_email = st.session_state.user_email
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(user_email)
    
    st.title("📟 JDL Intelligence Terminal")
    df_raw = load_portfolio(user_email)
    
    if not df_raw.empty:
        weights = {'abs': st.session_state.w_abs, 'mom': st.session_state.w_mom, 'div': st.session_state.w_div}
        calc_cols = ["supply change number(%)", "price change number(%)", "Score", "Reason", "Daily sales"]
        df_clean = df_raw.drop(columns=[c for c in calc_cols if c in df_raw.columns])
        metrics = df_clean.apply(lambda row: calculate_metrics(user_email, row, weights), axis=1)
        df_display = pd.concat([df_clean, metrics], axis=1)
    else:
        df_display = df_raw

    t = st.tabs(["🛰️ Predictor", "🏠 Homepage", "⚙️ Management"])
    
    with t[0]:
        if not df_display.empty:
            st.dataframe(df_display.sort_values("Score", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("Use Homepage to add items from the database.")

    with t[1]:
        st.subheader("Add/Manage Database Entries")
        if DB_DATA:
            # Strictly allow entries from csgo_api_v47.json
            valid_items = sorted(list(DB_DATA.keys()))
            
            with st.form("add_item_form"):
                new_item_name = st.selectbox("Select Item from Database", [""] + valid_items)
                e_p = st.number_input("Entry Price", value=0.0)
                e_s = st.number_input("Entry Supply", value=0)
                e_d = st.date_input("Entry Date", datetime.date.today())
                
                if st.form_submit_button("✅ Add Item"):
                    if new_item_name and new_item_name not in df_raw["Name of"].values:
                        new_row = pd.DataFrame([{
                            "Name of": new_item_name, "Entry price": e_p, "Entry supply": e_s,
                            "Current price": 0, "current supply": 0, "Entry date": e_d.strftime("%Y-%m-%d")
                        }])
                        df_updated = pd.concat([df_raw, new_row], ignore_index=True)
                        save_portfolio(user_email, df_updated)
                        st.success(f"{new_item_name} added!")
                        st.rerun()
                    elif not new_item_name:
                        st.error("Please select an item.")
                    else:
                        st.warning("Item already in portfolio.")
        else:
            st.error(DB_ERROR or "Database file missing.")

    with t[2]:
        st.subheader("⚙️ API Configuration")
        api_input = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(user_email, api_input)
            st.session_state.api_key = api_input
            st.success("API Key saved.")

        st.divider()
        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, err = fetch_market_data(row['Name of'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Current price"] = data["price"]
                        df_raw.at[idx, "current supply"] = data["supply"]
                        save_history_entry(user_email, row["Name of"], data["price"], data["supply"])
                    p.progress((i + 1) / len(df_raw))
                    time.sleep(1.2)
                save_portfolio(user_email, df_raw)
                st.success("Database Sync Complete")
                st.rerun()

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    else: user_dashboard()

if __name__ == "__main__":
    main()