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
# Single price endpoint for targeted item retrieval
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

def load_portfolio(user_email):
    cols = ["Item Name", "Type", "AT Price", "AT Supply", "Sess Price", "Sess Supply", "Price (CNY)", "Supply", "Daily Sales", "Last Updated"]
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

def load_history(user_email):
    path = get_user_history_path(user_email)
    if path and os.path.exists(path):
        try: 
            df = pd.read_csv(path, encoding="utf-8-sig")
            df['Date'] = pd.to_datetime(df['Date'])
            return df
        except: pass
    return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])

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
    """Calculates sales based on supply drops in history"""
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

def get_prediction_metrics(user_email, row, weights):
    """Calculates momentum and supply choke score"""
    # AT Values = Analysis Base Points
    e_price, e_supply = row["AT Price"], row["AT Supply"]
    c_price, c_supply = row["Price (CNY)"], row["Supply"]
    
    b_3h, b_today, b_yest = get_bought_momentum(user_email, row['Item Name'])
    
    # Supply Choke calculation
    s_pct = (e_supply - c_supply) / max(1, e_supply)
    abs_pts = np.clip((s_pct * 100) * 10, 0, 100) 

    # Momentum logic
    mom_pts = 100 if b_today > b_yest and b_today > 0 else (50 if b_3h > 0 else 0)
    
    total = round((abs_pts * weights['abs']) + (mom_pts * weights['mom']), 1)
    status = "🥇 THE BEST" if total >= 80 else ("❌ THE WORST" if total < 15 else "⚖️ NEUTRAL")
    
    return {"score": total, "reason": status, "Daily Sales": b_today}

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
        return None, f"HTTP {r.status_code}"
    except Exception as e: return None, str(e)

# --- USER DASHBOARD ---
def user_dashboard():
    user_email = st.session_state.user_email
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(user_email)
    
    st.title("📟 JDL Intelligence Terminal")
    df_raw = load_portfolio(user_email)
    
    if not df_raw.empty:
        weights = {'abs': st.session_state.w_abs, 'mom': st.session_state.w_mom, 'div': st.session_state.w_div}
        # Update Sales and Scores dynamically
        pred_res = df_raw.apply(lambda row: get_prediction_metrics(user_email, row, weights), axis=1, result_type='expand')
        # Combine predictions with original data
        for col in ["score", "reason", "Daily Sales"]:
            if col in pred_res.columns:
                df_raw[col] = pred_res[col]

    t = st.tabs(["🛰️ Predictor", "🏠 Homepage", "⚙️ Management"])
    
    with t[0]:
        if not df_raw.empty:
            st.dataframe(df_raw.sort_values("score", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("Add items in Homepage")

    with t[2]:
        st.subheader("🔑 API Key")
        api_input = st.text_input("Enter SteamDT Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(user_email, api_input)
            st.session_state.api_key = api_input
            st.success("Key Saved")

        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                # Update Session values before starting new fetch
                df_raw["Sess Price"] = df_raw["Price (CNY)"]
                df_raw["Sess Supply"] = df_raw["Supply"]
                
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, err = fetch_market_data(row['Item Name'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Price (CNY)"] = data["price"]
                        df_raw.at[idx, "Supply"] = data["supply"]
                        df_raw.at[idx, "Last Updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_history_entry(user_email, row["Item Name"], data["price"], data["supply"])
                    p.progress((i + 1) / len(df_raw))
                    time.sleep(1.2)
                
                save_portfolio(user_email, df_raw)
                st.success("Sync Complete")
                st.rerun()

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    else: user_dashboard()

if __name__ == "__main__":
    main()