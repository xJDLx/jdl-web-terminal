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
    """Loads the valid item list from csgo_api_v47.json"""
    if not os.path.exists(DB_FILE): return [], "❌ Database Not Found"
    try:
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        # Extract item names assuming 'items' is a list of strings or objects with a 'name' key
        items = data.get("items", [])
        if items and isinstance(items[0], dict):
            return sorted([item.get("name", "") for item in items if item.get("name")]), None
        return sorted(items), None
    except Exception as e: return [], str(e)

def load_portfolio(user_email):
    cols = ["Item Name", "Current Price (CNY)", "Listed Volume", "24h Price Change (%)", "7d Price Change (%)", "Last Updated"]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            for c in cols:
                if c not in df.columns: 
                    df[c] = 0.0 if "Price" in c or "%" in c else 0
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_portfolio(user_email, df):
    path = get_user_portfolio_path(user_email)
    if path: df.to_csv(path, index=False, encoding="utf-8-sig")

def fetch_steamdt_market_data(item_hash, api_key):
    try:
        encoded_name = urllib.parse.quote(item_hash)
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"{STEAMDT_BASE_URL}?marketHashName={encoded_name}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            item_meta = res.get("item", {})
            if not data: return None, "No market data"
            buff_data = next((m for m in data if m['platform'] == "BUFF"), data[0])
            return {
                "price": buff_data.get('sellPrice', 0),
                "volume": sum(m.get('sellCount', 0) for m in data),
                "p_24h": item_meta.get('price24hChange', 0.0),
                "p_7d": item_meta.get('price7dChange', 0.0),
                "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }, None
        return None, f"HTTP {r.status_code}"
    except Exception as e: return None, str(e)

def color_price_change(val):
    color = 'lightgreen' if val > 0 else ('lightcoral' if val < 0 else 'transparent')
    return f'background-color: {color}'

# --- USER DASHBOARD ---
def user_dashboard():
    # Load items from local JSON database
    db_items, db_err = load_local_database()
    user_email = st.session_state.user_email
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(user_email)
    
    st.title("📟 JDL Intelligence Terminal")
    df_raw = load_portfolio(user_email)
    
    t = st.tabs(["🛰️ Monitor", "🏠 Manage Items", "⚙️ Settings"])
    
    with t[0]:
        if not df_raw.empty:
            styled_df = df_raw.style.map(color_price_change, subset=["24h Price Change (%)", "7d Price Change (%)"]).format(precision=2)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else: st.info("Monitor is empty.")

    with t[1]:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Add Item from Database")
            if db_err: st.error(db_err)
            else:
                # Restrict input to existing database items via searchable dropdown
                selected_item = st.selectbox("Select Item", options=[""] + db_items, index=0)
                if st.button("✅ Add Selected"):
                    if not st.session_state.api_key: st.error("Add API Key in Settings.")
                    elif selected_item and selected_item not in df_raw["Item Name"].values:
                        data, err = fetch_steamdt_market_data(selected_item, st.session_state.api_key)
                        if data:
                            new_row = pd.DataFrame([{
                                "Item Name": selected_item,
                                "Current Price (CNY)": data['price'],
                                "Listed Volume": data['volume'],
                                "24h Price Change (%)": data['p_24h'],
                                "7d Price Change (%)": data['p_7d'],
                                "Last Updated": data['updated']
                            }])
                            df_updated = pd.concat([df_raw, new_row], ignore_index=True)
                            save_portfolio(user_email, df_updated)
                            st.rerun()
                        else: st.error(err)
        with col_b:
            st.subheader("Remove Item")
            if not df_raw.empty:
                to_delete = st.selectbox("Select to Delete", [""] + df_raw["Item Name"].tolist())
                if st.button("🗑️ Delete"):
                    df_updated = df_raw[df_raw["Item Name"] != to_delete]
                    save_portfolio(user_email, df_updated)
                    st.rerun()

    with t[2]:
        st.subheader("⚙️ Settings")
        api_input = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
        if st.button("💾 Save Key"):
            save_api_key(user_email, api_input)
            st.session_state.api_key = api_input
            st.success("Key saved.")

        if st.button("🔄 Sync Market Data"):
            if not st.session_state.api_key: st.error("No API Key")
            else:
                p_bar = st.progress(0)
                for i, (idx, row) in enumerate(df_raw.iterrows()):
                    data, _ = fetch_steamdt_market_data(row['Item Name'], st.session_state.api_key)
                    if data:
                        df_raw.at[idx, "Current Price (CNY)"] = data['price']
                        df_raw.at[idx, "Listed Volume"] = data['volume']
                        df_raw.at[idx, "24h Price Change (%)"] = data['p_24h']
                        df_raw.at[idx, "7d Price Change (%)"] = data['p_7d']
                        df_raw.at[idx, "Last Updated"] = data['updated']
                    p_bar.progress((i + 1) / len(df_raw))
                    time.sleep(1.2)
                save_portfolio(user_email, df_raw)
                st.rerun()

def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
    else: user_dashboard()

if __name__ == "__main__":
    main()