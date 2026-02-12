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
# Updated to the official single price endpoint
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
    # Updated Headers
    cols = ["Item name", "Entry price", "Entry supply", "Current price", "current supply", 
            "supply change number(%)", "price change number(%)", "Entry date", "Score", "Reason", "Daily sales"]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            for c in cols:
                if c not in df.columns: df[c] = 0 if "(%)" not in c else 0.0
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_portfolio(user_email, df):
    path = get_user_portfolio_path(user_email)
    if path: 
        save_cols = ["Item name", "Entry price", "Entry supply", "Current price", "current supply", 
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
    # Mapping requested headers to calculation logic
    e_price, e_supply = row["Entry price"], row["Entry supply"]
    c_price, c_supply = row["Current price"], row["current supply"]
    
    # Calculate Changes (%)
    supply_change = ((e_supply - c_supply) / max(1, e_supply)) * 100
    price_change = ((c_price - e_price) / max(0.01, e_price)) * 100
    
    b_3h, b_today, b_yest = get_bought_momentum(user_email, row['Item name'])
    
    # Predictor Logic
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
        # Align with doc.steamdt.com schema
        encoded_name = urllib.parse.quote(item_hash)
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{STEAMDT_BASE_URL}?marketHashName={encoded_name}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            if not data: return None, "No data"
            # Prioritize BUFF price
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
        # Drop calculated columns to prevent duplicate column error
        calc_cols = ["supply change number(%)", "price change number(%)", "Score", "Reason", "Daily sales"]
        df_clean = df_raw.drop(columns=[c for c in calc_cols if c in df_raw.columns])
        # Recalculate based on requested metrics
        metrics = df_clean.apply(lambda row: calculate_metrics(user_email, row, weights), axis=1)
        df_display = pd.concat([df_clean, metrics], axis=1)
    else:
        df_display = df_raw

    t = st.tabs(["🛰️ Predictor", "🏠 Homepage", "⚙️ Management"])
    
    with t[0]:
        if not df_display.empty:
            st.dataframe(df_display.sort_values("Score", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("Use Homepage to add items and Entry points.")

    with t[1]:
        st.subheader("Manage Entry Points")
        if not df_raw.empty:
            with st.form("entry_data_form"):
                item_to_edit = st.selectbox("Select Item", df_raw["Item name"].tolist())
                current_row = df_raw[df_raw["Item name"] == item_to_edit].iloc[0]
                
                new_entry_p = st.number_input("Entry Price", value=float(current_row.get("Entry price", 0.0)))
                new_entry_s = st.number_input("Entry Supply", value=int(current_row.get("Entry supply", 0)))
                new_entry_d = st.text_input("Entry Date", value=str(current_row.get("Entry date", datetime.datetime.now().strftime("%Y-%m-%d"))))
                
                if st.form_submit_button("Update Entry Points"):
                    df_raw.loc[df_raw["Item name"] == item_to_edit, ["Entry price", "Entry supply", "Entry date"]] = [new_entry_p, new_entry_s, new_entry_d]
                    save_portfolio(user_email, df_raw)
                    st.success("Entry updated!")
                    st.rerun()

    with t[2]:
        st.subheader("🔑 API Configuration")
        api_input = st.text_input("Enter SteamDT Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(user_email, api_input)
            st.session_state.api_key = api_input
            st.success("Key Saved")

        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, err = fetch_market_data(row['Item name'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Current price"] = data["price"]
                        df_raw.at[idx, "current supply"] = data["supply"]
                        save_history_entry(user_email, row["Item name"], data["price"], data["supply"])
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