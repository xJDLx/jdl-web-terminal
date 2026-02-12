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
    """Create and return user-specific secure folder path"""
    if not user_email: return None
    
    # Create base user data directory if it doesn't exist
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, mode=0o700)  # Secure permissions
        
    # Create user-specific folder
    user_folder = os.path.join(USER_DATA_DIR, user_email.replace("@", "_at_").replace(".", "_dot_"))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, mode=0o700)  # Secure permissions
        
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
# Increased TTL to 300 seconds (5 minutes) to prevent hitting Google Sheets API quotas
conn = st.connection("gsheets", type=GSheetsConnection, ttl=300)

for key, val in [("admin_verified", False), ("user_verified", False), 
                 ("user_email", None), ("user_name", None),
                 ("w_abs", DEFAULT_WEIGHTS['abs']), ("w_mom", DEFAULT_WEIGHTS['mom']), 
                 ("w_div", DEFAULT_WEIGHTS['div']), ("api_key", "")]:
    if key not in st.session_state:
        st.session_state[key] = val
>>>>>>> ae1f6abd49e9bb20acfccff947b76d06cd259ca0

=======
for key, val in [("admin_verified", False), ("user_verified", False), 
                 ("user_email", None), ("user_name", None),
                 ("w_abs", DEFAULT_WEIGHTS['abs']), ("w_mom", DEFAULT_WEIGHTS['mom']), 
                 ("w_div", DEFAULT_WEIGHTS['div']), ("api_key", "")]:
    if key not in st.session_state:
        st.session_state[key] = val
>>>>>>> ae1f6abd49e9bb20acfccff947b76d06cd259ca0

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

def save_history_entry(user_email, item_name, price, supply, sales):
    df_hist = load_history(user_email)
    new_entry = pd.DataFrame([{
        "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "Item Name": item_name, "Price (CNY)": price, 
        "Supply": supply, "Sales Detected": sales
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

def get_prediction_metrics(user_email, row, weights):
    item_name, e_price, e_supply = row['Item Name'], row["AT Price"], row["AT Supply"]
    c_price, c_supply = row["Price (CNY)"], row["Supply"]
    
    b_3h, b_today, b_yest = get_bought_momentum(user_email, item_name)
    s_pct = (e_supply - c_supply) / max(1, e_supply)
    abs_pts = np.clip((s_pct * 100) * 10, 0, 100) 

    mom_pts = 100 if b_today > b_yest and b_today > 0 else (50 if b_3h > 0 else 0)
    p_pct = (c_price - e_price) / max(1, e_price)
    gap = s_pct - p_pct
    div_pts = np.clip(gap * 500, 0, 100) if gap > 0 else 0

    total = round((abs_pts * weights['abs']) + (mom_pts * weights['mom']) + (div_pts * weights['div']), 1)
    status = "🥇 THE BEST" if total >= 80 else ("📈 STRENGTHENING" if total >= 50 else ("❌ THE WORST" if total < 15 and s_pct < -0.05 else "⚖️ NEUTRAL"))
    
    return {"score": total, "reason": status, "trend": "✅" if total >= 80 else "➖", "breakdown": f"A:{int(abs_pts)}|M:{int(mom_pts)}|D:{int(div_pts)}", "3h": b_3h, "today": b_today, "yesterday": b_yest}

def fetch_market_data(item_hash, api_key):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        r = requests.get(STEAMDT_BASE_URL, params={"marketHashName": item_hash}, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if not data: return None, "Not Found"
            price = next((m['sellPrice'] for m in data if m['platform'] == "BUFF"), data[0]['sellPrice'])
            supply = sum(m.get("sellCount", 0) for m in data)
            return {"price": price, "supply": supply}, None
        return None, f"Error {r.status_code}"
    except: return None, "Request Failed"

# --- MAIN DASHBOARD LOGIC ---
def admin_dashboard():
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.admin_verified = False
            st.rerun()
    
    st.title("🔐 Admin Dashboard")
    try:
        # Utilizing cached read to avoid API rate limits
        df_users = conn.read(worksheet="Sheet1", ttl=300)
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")
        st.stop()
    
    tabs = st.tabs(["📊 Overview", "👥 Users", "⏳ Pending", "⚙️ Settings"])
    
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Users", len(df_users))
        c2.metric("Approved", len(df_users[df_users['Status'] == 'Approved']))
        c3.metric("Pending", len(df_users[df_users['Status'] == 'Pending']))
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    with tabs[3]:
        if st.button("🧹 Reset Sessions"):
            df_users['Session'] = 'Offline'
            conn.update(worksheet="Sheet1", data=df_users)
            st.success("Sessions Reset")

def user_dashboard():
    DB_DATA, DB_ERROR = load_local_database()
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(st.session_state.user_email)
    
    st.title("📟 JDL Intelligence Terminal")
    df_raw = load_portfolio(st.session_state.user_email)
    
    if not df_raw.empty:
        weights = {'abs': st.session_state.w_abs, 'mom': st.session_state.w_mom, 'div': st.session_state.w_div}
        pred_res = df_raw.apply(lambda row: get_prediction_metrics(st.session_state.user_email, row, weights), axis=1, result_type='expand')
        df_raw = pd.concat([df_raw, pred_res], axis=1)

    t = st.tabs(["🛰️ Predictor", "📅 Daily", "🏛️ Permanent", "⚙️ Management"])
    
    with t[0]:
        if not df_raw.empty:
            st.dataframe(df_raw.sort_values("score", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("Add items in Management")

    with t[3]:
        with st.expander("🎯 Strategy Tuner"):
            st.session_state.w_abs = st.slider("Supply Choke", 0.0, 1.0, st.session_state.w_abs)
            st.session_state.w_mom = st.slider("Momentum", 0.0, 1.0, st.session_state.w_mom)
            st.session_state.w_div = st.slider("Price Lag", 0.0, 1.0, st.session_state.w_div)
        
        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: st.error("Set API Key")
            else:
                p = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, err = fetch_market_data(row['Item Name'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Price (CNY)"], df_raw.at[idx, "Supply"] = data["price"], data["supply"]
                        save_history_entry(st.session_state.user_email, row["Item Name"], data["price"], data["supply"], 0)
                    p.progress((i + 1) / len(df_raw))
                    time.sleep(2)
                save_portfolio(st.session_state.user_email, df_raw)
                st.success("Sync Complete")

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    elif st.session_state.admin_verified: admin_dashboard()
    else: user_dashboard()

if __name__ == "__main__":
    main()
