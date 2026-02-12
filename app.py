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
CSV_FILE = "portfolio.csv"
HISTORY_FILE = "history.csv"
DB_FILE = "csgo_api_v47.json"
CONFIG_FILE = "api_key.txt"
STEAMDT_BASE_URL = "https://open.steamdt.com/open/cs2/v1/price/single"

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

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

# --- CORE ENGINE FUNCTIONS ---
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
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, list):
            return { (item.get("name") or item.get("market_hash_name")): item for item in data }, None
        return data, None
    except Exception as e: return None, str(e)

def load_portfolio():
    required = ["Item Name", "Type", "AT Price", "AT Supply", "Sess Price", "Sess Supply", "Price (CNY)", "Supply", "Daily Sales", "Last Updated"]
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
        for col in required:
            if col not in df.columns: df[col] = 0
        return df[required]
    return pd.DataFrame(columns=required)

def save_portfolio(df):
    df.to_csv(CSV_FILE, index=False)

def load_history():
    if os.path.exists(HISTORY_FILE): 
        try: 
            df_h = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
            df_h['Date'] = pd.to_datetime(df_h['Date'])
            return df_h
        except: return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])
    return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])

def save_history_entry(item_name, price, supply, sales_detected):
    df_hist = load_history()
    new_entry = pd.DataFrame([{
        "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "Item Name": item_name, "Price (CNY)": price, 
        "Supply": supply, "Sales Detected": sales_detected
    }])
    pd.concat([df_hist, new_entry], ignore_index=True).to_csv(HISTORY_FILE, index=False)

def get_bought_momentum(item_name):
    df_h = load_history()
    if df_h.empty: return 0, 0, 0
    item_data = df_h[df_h["Item Name"] == item_name].sort_values("Date")
    if len(item_data) < 2: return 0, 0, 0
    
    item_data['diff'] = item_data['Supply'].shift(1) - item_data['Supply']
    item_data['buys'] = item_data['diff'].apply(lambda x: x if x > 0 else 0)
    
    now = datetime.datetime.now()
    t_3h = now - datetime.timedelta(hours=3)
    t_24 = now - datetime.timedelta(hours=24)
    
    past_3h = item_data[item_data["Date"] >= t_3h]
    bought_3h = past_3h['buys'].sum() if not past_3h.empty else item_data['buys'].sum()
    bought_today = item_data[item_data["Date"] >= t_24.replace(hour=0, minute=0)]['buys'].sum()
    
    y_start = (t_24 - datetime.timedelta(days=1)).replace(hour=0, minute=0)
    bought_yesterday = item_data[(item_data["Date"] >= y_start) & 
                                 (item_data["Date"] < t_24.replace(hour=0, minute=0))]['buys'].sum()
    
    return int(bought_3h), int(bought_today), int(bought_yesterday)

def get_prediction_metrics(row, weights):
    item_name, e_price, e_supply = row['Item Name'], row["AT Price"], row["AT Supply"]
    c_price, c_supply = row["Price (CNY)"], row["Supply"]
    
    df_h = load_history()
    sync_count = len(df_h[df_h["Item Name"] == item_name])
    b_3h, b_today, b_yest = get_bought_momentum(item_name)
    
    s_pct = (e_supply - c_supply) / max(1, e_supply)
    abs_pts = np.clip((s_pct * 100) * 10, 0, 100) 

    if b_today > b_yest and b_today > 0: mom_pts = 100
    elif b_3h > 0: mom_pts = 50
    else: mom_pts = 0

    p_pct = (c_price - e_price) / max(1, e_price)
    gap = s_pct - p_pct
    div_pts = np.clip(gap * 500, 0, 100) if gap > 0 else 0

    total = (abs_pts * weights['abs']) + (mom_pts * weights['mom']) + (div_pts * weights['div'])
    total = round(total, 1)
    breakdown = f"A:{int(abs_pts)}|M:{int(mom_pts)}|D:{int(div_pts)}"
    
    if total >= 80: status, trend = "🥇 THE BEST: PUMP READY", "✅"
    elif total >= 50: status, trend = "📈 STRENGTHENING", "🔺"
    elif total < 15 and s_pct < -0.05: status, trend = "❌ THE WORST: DUMPING", "⚠️"
    else: status, trend = "⚖️ NEUTRAL", "➖"
    
    return {"score": total, "reason": status, "trend": trend, "breakdown": breakdown, 
            "3h": b_3h, "today": b_today, "yesterday": b_yest, "syncs": sync_count}

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

# --- SESSION STATE INITIALIZATION ---
if "w_abs" not in st.session_state: st.session_state.w_abs = DEFAULT_WEIGHTS['abs']
if "w_mom" not in st.session_state: st.session_state.w_mom = DEFAULT_WEIGHTS['mom']
if "w_div" not in st.session_state: st.session_state.w_div = DEFAULT_WEIGHTS['div']
if "api_key" not in st.session_state: st.session_state.api_key = load_api_key()

# --- MAIN APP ---
def main():
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
        return

    # Load data
    DB_DATA, DB_ERROR = load_local_database()
    st.title("📟 JDL Intelligence Terminal")
    
    df_raw = load_portfolio()
    current_weights = {'abs': st.session_state.w_abs, 'mom': st.session_state.w_mom, 'div': st.session_state.w_div}
    
    if not df_raw.empty:
        df_raw["Market Chart"] = df_raw["Item Name"].apply(lambda x: f"https://steamdt.com/cs2/{x}")
        pred_res = df_raw.apply(get_prediction_metrics, axis=1, args=(current_weights,), result_type='expand')
        df_raw["Score"], df_raw["Signal"], df_raw["Trend"], df_raw["Breakdown"], df_raw["3H"], df_raw["Today"], df_raw["Yesterday"], df_raw["Syncs"] = \
            pred_res["score"], pred_res["reason"], pred_res["trend"], pred_res["breakdown"], pred_res["3h"], pred_res["today"], pred_res["yesterday"], pred_res["syncs"]
    
    tabs = st.tabs(["🛰️ Predictor", "📅 Daily", "🏛️ Permanent", "⚙️ Management"])
    
    col_cfg = {
        "Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.0f"),
        "3H": st.column_config.NumberColumn("Bought 3H", format="%d ⚡"),
        "Today": st.column_config.NumberColumn("Bought Today", format="%d 🔥"),
        "Market Chart": st.column_config.LinkColumn("SteamDT", display_text="Link"),
        "Price %": st.column_config.NumberColumn("Price %", format="%.2f%%"),
        "Supply %": st.column_config.NumberColumn("Supply %", format="%.2f%%")
    }
    
    def render_tab_view(df, p_col, s_col):
        cols = ["Trend", "Score", "Signal", "Syncs", "Breakdown", "Item Name", p_col, "Price (CNY)", "Price %", s_col, "Supply", "Supply %", "Market Chart"]
        for cat, title in [("Inventory", "### 🎒 Inventory"), ("Watchlist", "### 🔭 Watchlist")]:
            sub_df = df[df["Type"] == cat]
            if not sub_df.empty:
                st.markdown(title)
                st.dataframe(sub_df[cols], use_container_width=True, column_config=col_cfg, hide_index=True)
    
    # --- TAB CONTENT ---
    with tabs[0]:  # PREDICTOR
        if not df_raw.empty:
            radar_df = df_raw.copy().sort_values("Score", ascending=False)
            m1, m2, m3 = st.columns(3)
            m1.metric("🥇 TOP PICK", radar_df.iloc[0]["Item Name"], f"Score: {radar_df.iloc[0]['Score']}")
            m2.metric("📊 AVG Confidence", f"{radar_df['Score'].mean():.1f}")
            m3.metric("⚠️ BOTTOM PICK", radar_df.iloc[-1]["Item Name"], f"{radar_df.iloc[-1]['Score']}", delta_color="inverse")
            
            st.dataframe(radar_df[["Trend", "Score", "Signal", "Breakdown", "Item Name", "Price (CNY)", "Supply", "3H", "Today", "Market Chart"]], 
                         use_container_width=True, column_config=col_cfg, hide_index=True)
        else:
            st.info("📭 No items in portfolio. Add items in Management tab.")
    
    with tabs[1]:  # DAILY (Sess Data)
        if not df_raw.empty:
            df_d = df_raw.copy()
            df_d["Price %"] = ((df_d["Price (CNY)"] - df_d["Sess Price"]) / df_d["Sess Price"]) * 100
            df_d["Supply %"] = ((df_d["Supply"] - df_d["Sess Supply"]) / df_d["Sess Supply"]) * 100
            render_tab_view(df_d, "Sess Price", "Sess Supply")
        else:
            st.info("📭 No items in portfolio. Add items in Management tab.")
    
    with tabs[2]:  # PERMANENT (AT Data)
        if not df_raw.empty:
            df_p = df_raw.copy()
            df_p["Price %"] = ((df_p["Price (CNY)"] - df_p["AT Price"]) / df_p["AT Price"]) * 100
            df_p["Supply %"] = ((df_p["Supply"] - df_p["AT Supply"]) / df_p["AT Supply"]) * 100
            render_tab_view(df_p, "AT Price", "AT Supply")
        else:
            st.info("📭 No items in portfolio. Add items in Management tab.")
    
    with tabs[3]:  # MANAGEMENT
        st.header("⚙️ Terminal Management")
        
        with st.expander("🎯 Intelligence Strategy Tuner", expanded=True):
            st.session_state.w_abs = st.slider("Absorption (Supply Choke)", 0.0, 1.0, st.session_state.w_abs, help="Weight for supply absorption metric")
            st.session_state.w_mom = st.slider("Momentum (Recent Sales)", 0.0, 1.0, st.session_state.w_mom, help="Weight for buying momentum")
            st.session_state.w_div = st.slider("Divergence (Price Lag)", 0.0, 1.0, st.session_state.w_div, help="Weight for price-supply divergence")
            
            total_w = st.session_state.w_abs + st.session_state.w_mom + st.session_state.w_div
            if total_w > 0:
                st.info(f"Normalized: A:{st.session_state.w_abs/total_w:.1%} | M:{st.session_state.w_mom/total_w:.1%} | D:{st.session_state.w_div/total_w:.1%}")
            
            if st.button("♻️ Reset to Defaults"):
                st.session_state.w_abs, st.session_state.w_mom, st.session_state.w_div = 0.4, 0.3, 0.3
                st.rerun()
        
        if st.button("🔄 Global Sync"):
            if not st.session_state.api_key: 
                st.error("❌ No API Key. Set it below first.")
            elif df_raw.empty:
                st.error("❌ No items to sync.")
            else:
                prog = st.progress(0); status = st.empty()
                for i, row in df_raw.iterrows():
                    status.text(f"Updating {row['Item Name']}..."); 
                    data, err = fetch_market_data(row["Item Name"], st.session_state.api_key)
                    if data:
                        df_raw.at[i, "Price (CNY)"] = data["price"]
                        df_raw.at[i, "Supply"] = data["supply"]
                        save_history_entry(row["Item Name"], data["price"], data["supply"], 0)
                    prog.progress((i + 1) / len(df_raw)); 
                    time.sleep(3)
                save_portfolio(df_raw); st.success("✅ Sync Complete!"); st.rerun()
        
        with st.expander("🔑 API Key Setup"):
            new_key = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
            if st.button("💾 Save Key"): 
                save_api_key(new_key); st.session_state.api_key = new_key; st.success("✅ Saved!")
        
        with st.expander("➕ Add New Item"):
            if DB_DATA:
                new_item = st.selectbox("Select Item", options=list(DB_DATA.keys()))
                itype = st.radio("Category", ["Inventory", "Watchlist"])
                if st.button("Add Item"):
                    init, err = fetch_market_data(new_item, st.session_state.api_key)
                    if init:
                        new_row = {
                            "Item Name": new_item, "Type": itype, "AT Price": init["price"], 
                            "AT Supply": init["supply"], "Sess Price": init["price"], 
                            "Sess Supply": init["supply"], "Price (CNY)": init["price"], 
                            "Supply": init["supply"], "Daily Sales": 0, 
                            "Last Updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        df_raw = pd.concat([df_raw, pd.DataFrame([new_row])], ignore_index=True)
                        save_portfolio(df_raw); 
                        st.success(f"✅ Added {new_item}"); 
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")
            else:
                st.error(f"❌ {DB_ERROR}")

if __name__ == "__main__":
    main()