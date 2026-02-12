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
USER_DATA_DIR = "user_data"  # Directory for per-user data

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
    """Create and return user-specific folder path"""
    if not user_email:
        return None
    user_folder = os.path.join(USER_DATA_DIR, user_email.replace("@", "_at_").replace(".", "_dot_"))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_portfolio_path(user_email):
    """Get user's private portfolio file path"""
    user_folder = get_user_folder(user_email)
    return os.path.join(user_folder, "portfolio.csv") if user_folder else None

def get_user_history_path(user_email):
    """Get user's private history file path"""
    user_folder = get_user_folder(user_email)
    return os.path.join(user_folder, "history.csv") if user_folder else None

def get_user_api_key_path(user_email):
    """Get user's private API key file path"""
    user_folder = get_user_folder(user_email)
    return os.path.join(user_folder, "api_key.txt") if user_folder else None

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- SESSION STATE INITIALIZATION ---
if "admin_verified" not in st.session_state: 
    st.session_state.admin_verified = False
if "user_verified" not in st.session_state: 
    st.session_state.user_verified = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "w_abs" not in st.session_state: 
    st.session_state.w_abs = DEFAULT_WEIGHTS['abs']
if "w_mom" not in st.session_state: 
    st.session_state.w_mom = DEFAULT_WEIGHTS['mom']
if "w_div" not in st.session_state: 
    st.session_state.w_div = DEFAULT_WEIGHTS['div']
if "api_key" not in st.session_state: 
    st.session_state.api_key = ""


# --- CORE ENGINE FUNCTIONS ---
def load_api_key(user_email):
    """Load user's private API key"""
    if not user_email:
        return ""
    api_key_path = get_user_api_key_path(user_email)
    if api_key_path and os.path.exists(api_key_path):
        with open(api_key_path, "r") as f:
            return f.read().strip()
    return ""

def save_api_key(user_email, key):
    """Save user's private API key"""
    if not user_email:
        return
    api_key_path = get_user_api_key_path(user_email)
    if api_key_path:
        with open(api_key_path, "w") as f:
            f.write(key.strip())

@st.cache_data(ttl=3600)
def load_local_database():
    if not os.path.exists(DB_FILE): return None, "❌ Database Not Found"
    try:
        with open(DB_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, list):
            return { (item.get("name") or item.get("market_hash_name")): item for item in data }, None
        elif isinstance(data, dict) and "items" in data:
            # Handle {"items": ["item1", "item2", ...]} format
            items = data.get("items", [])
            if isinstance(items[0], str) if items else False:
                # Simple list of strings
                return {item: {"name": item} for item in items}, None
            else:
                # List of objects
                return {(item.get("name") or item.get("market_hash_name")): item for item in items}, None
        return data, None
    except Exception as e: return None, str(e)

def load_portfolio(user_email):
    """Load user's private portfolio"""
    required = ["Item Name", "Type", "AT Price", "AT Supply", "Sess Price", "Sess Supply", "Price (CNY)", "Supply", "Daily Sales", "Last Updated"]
    if not user_email:
        return pd.DataFrame(columns=required)
    
    portfolio_path = get_user_portfolio_path(user_email)
    if portfolio_path and os.path.exists(portfolio_path):
        try:
            df = pd.read_csv(portfolio_path, encoding="utf-8-sig")
            for col in required:
                if col not in df.columns: df[col] = 0
            return df[required]
        except:
            return pd.DataFrame(columns=required)
    return pd.DataFrame(columns=required)

def save_portfolio(user_email, df):
    """Save user's private portfolio"""
    if not user_email:
        return
    portfolio_path = get_user_portfolio_path(user_email)
    if portfolio_path:
        df.to_csv(portfolio_path, index=False, encoding="utf-8-sig")

def load_history(user_email):
    """Load user's private history"""
    if not user_email:
        return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])
    
    history_path = get_user_history_path(user_email)
    if history_path and os.path.exists(history_path):
        try: 
            df_h = pd.read_csv(history_path, encoding="utf-8-sig")
            df_h['Date'] = pd.to_datetime(df_h['Date'])
            return df_h
        except:
            return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])
    return pd.DataFrame(columns=["Date", "Item Name", "Price (CNY)", "Supply", "Sales Detected"])


def save_history_entry(user_email, item_name, price, supply, sales_detected):
    """Save user's private history entry"""
    if not user_email:
        return
    df_hist = load_history(user_email)
    new_entry = pd.DataFrame([{
        "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "Item Name": item_name, "Price (CNY)": price, 
        "Supply": supply, "Sales Detected": sales_detected
    }])
    updated = pd.concat([df_hist, new_entry], ignore_index=True)
    history_path = get_user_history_path(user_email)
    if history_path:
        updated.to_csv(history_path, index=False, encoding="utf-8-sig")

def save_local_database(db_data):
    """Safely save database to JSON file"""
    try:
        db, _ = load_local_database()
        if db:
            # Extract just the item keys/names
            items = list(db.keys())
            with open(DB_FILE, "w", encoding="utf-8-sig") as f:
                json.dump({"items": items}, f, ensure_ascii=False, indent=2)
            st.cache_data.clear()  # Clear cache to reload
            return True, None
        return False, "Failed to load database"
    except Exception as e:
        return False, str(e)

def get_bought_momentum(user_email, item_name):
    """Get user's private item momentum data"""
    df_h = load_history(user_email)
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

def get_prediction_metrics(user_email, row, weights):
    """Get prediction metrics for user's private data"""
    item_name, e_price, e_supply = row['Item Name'], row["AT Price"], row["AT Supply"]
    c_price, c_supply = row["Price (CNY)"], row["Supply"]
    
    df_h = load_history(user_email)
    sync_count = len(df_h[df_h["Item Name"] == item_name])
    b_3h, b_today, b_yest = get_bought_momentum(user_email, item_name)
    
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
if "api_key" not in st.session_state: st.session_state.api_key = ""

# --- MAIN APP ---
def admin_dashboard():
    """Admin Management Dashboard"""
    st.set_page_config(page_title="JDL Admin Dashboard", layout="wide")
    
    # Add logout button in top right
    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.admin_verified = False
            st.session_state.user_verified = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.rerun()
    
    st.title("🔐 Admin Dashboard")
    st.markdown("---")
    
    # Admin tabs
    admin_tabs = st.tabs(["📊 Overview", "👥 User Management", "📋 Pending Requests", "🔍 Activity & Logs", "⚙️ Settings"])
    
    try:
        df_users = conn.read(worksheet="Sheet1", ttl=0)
    except:
        st.error("❌ Cannot connect to Google Sheets. Ensure credentials are configured.")
        return
    
    # --- TAB 1: OVERVIEW ---
    with admin_tabs[0]:
        st.subheader("System Overview")
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        
        total_users = len(df_users)
        approved = len(df_users[df_users['Status'] == 'Approved'])
        pending = len(df_users[df_users['Status'] == 'Pending'])
        online = len(df_users[df_users['Session'] == 'Online'])
        
        col1.metric("👥 Total Users", total_users)
        col2.metric("✅ Approved", approved)
        col3.metric("⏳ Pending", pending)
        col4.metric("🟢 Online", online)
        
        st.markdown("---")
        
        # Check for expiring soon users
        try:
            df_check = df_users[df_users['Status'] == 'Approved'].copy()
            expiring_soon = []
            for idx, user in df_check.iterrows():
                exp = user.get('Expiry')
                if exp and exp != "Pending Admin":
                    try:
                        exp_date = datetime.datetime.strptime(str(exp), "%Y-%m-%d")
                        days_left = (exp_date - datetime.datetime.now()).days
                        if 0 <= days_left <= 7:
                            expiring_soon.append((user['Name'], exp, days_left))
                    except:
                        pass
            
            if expiring_soon:
                st.warning("⚠️ **Memberships Expiring Soon (7 days or less):**")
                for name, exp, days in expiring_soon:
                    st.write(f"  • {name} - expires {exp} ({days} days left)")
        except:
            pass
        

        # Recent Activity
        st.subheader("Recent Activity")
        if 'Last Login' in df_users.columns:
            recent = df_users[['Name', 'Email', 'Status', 'Last Login', 'Session']].head(10)
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No activity data available")
    
    # --- TAB 2: USER MANAGEMENT ---
    with admin_tabs[1]:
        st.subheader("User Management")
        
        # Filter users
        status_filter = st.selectbox("Filter by Status", ["All", "Approved", "Pending", "Rejected"])
        
        if status_filter == "All":
            filtered_users = df_users
        else:
            filtered_users = df_users[df_users['Status'] == status_filter]
        
        st.write(f"Showing {len(filtered_users)} user(s)")
        
        # Display users with action buttons
        for idx, user in filtered_users.iterrows():
            with st.expander(f"📌 {user.get('Name', 'Unknown')} ({user.get('Email', 'N/A')})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Status:** {user.get('Status', 'N/A')}")
                    st.write(f"**Email:** {user.get('Email', 'N/A')}")
                    st.write(f"**Joined:** {user.get('Date', 'N/A')}")
                    st.write(f"**Requested:** {user.get('Requested Duration', 'N/A')}")
                
                with col2:
                    st.write(f"**Session:** {user.get('Session', 'Offline')}")
                    st.write(f"**Last Login:** {user.get('Last Login', 'Never')}")
                    st.write(f"**Expiry:** {user.get('Expiry', 'Pending')}")
                
                with col3:
                    # Action buttons
                    if user.get('Status') == 'Pending':
                        st.write("**Set Duration:**")
                        duration_days = st.selectbox(
                            "Membership Duration",
                            options=[30, 60, 90, 180, 365],
                            format_func=lambda x: {30: "30 days (1 month)", 60: "60 days (2 months)", 
                                                   90: "90 days (3 months)", 180: "180 days (6 months)", 
                                                   365: "365 days (1 year)"}[x],
                            key=f"duration_{idx}"
                        )
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button(f"✅ Approve", key=f"approve_{idx}"):
                                expiry_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).strftime("%Y-%m-%d")
                                df_users.at[idx, 'Status'] = 'Approved'
                                df_users.at[idx, 'Expiry'] = expiry_date
                                conn.update(worksheet="Sheet1", data=df_users)
                                st.success(f"✅ {user['Name']} approved until {expiry_date}")
                                st.rerun()
                        
                        with col_btn2:
                            if st.button(f"❌ Reject", key=f"reject_{idx}"):
                                df_users.at[idx, 'Status'] = 'Rejected'
                                conn.update(worksheet="Sheet1", data=df_users)
                                st.error(f"❌ {user['Name']} rejected")
                                st.rerun()
                    else:
                        # For already approved users, show edit option
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            if st.button(f"✏️ Edit", key=f"edit_{idx}"):
                                st.session_state[f"edit_{idx}"] = True
                        
                        with col_btn2:
                            if st.button(f"❌ Reject", key=f"reject_{idx}"):
                                df_users.at[idx, 'Status'] = 'Rejected'
                                conn.update(worksheet="Sheet1", data=df_users)
                                st.error(f"❌ {user['Name']} rejected")
                                st.rerun()
                        
                        with col_btn3:
                            if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                                df_users = df_users.drop(idx)
                                conn.update(worksheet="Sheet1", data=df_users)
                            st.warning(f"🗑️ {user['Name']} deleted")
                            st.rerun()
    
    # --- TAB 3: PENDING REQUESTS ---
    with admin_tabs[2]:
        st.subheader("Pending Access Requests")
        
        pending_users = df_users[df_users['Status'] == 'Pending']
        
        if len(pending_users) == 0:
            st.success("✅ No pending requests")
        else:
            st.warning(f"⚠️ {len(pending_users)} pending request(s)")
            
            for idx, user in pending_users.iterrows():
                st.markdown(f"### {user.get('Name', 'Unknown')}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"📧 **Email:** {user.get('Email', 'N/A')}")
                    st.write(f"📅 **Request Date:** {user.get('Date', 'N/A')}")
                
                with col2:
                    st.write(f"**Requested Duration:** {user.get('Requested Duration', 'Not specified')}")
                
                with col3:
                    st.write("**Grant Duration:**")
                    duration_days = st.selectbox(
                        "Select membership length",
                        options=[30, 60, 90, 180, 365],
                        format_func=lambda x: {30: "30 days", 60: "60 days", 90: "90 days", 180: "6 months", 365: "1 year"}[x],
                        key=f"pending_duration_{idx}"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button(f"✅ Approve", key=f"approve_pending_{idx}"):
                            expiry_date = (datetime.datetime.now() + datetime.timedelta(days=duration_days)).strftime("%Y-%m-%d")
                            df_users.at[idx, 'Status'] = 'Approved'
                            df_users.at[idx, 'Expiry'] = expiry_date
                            conn.update(worksheet="Sheet1", data=df_users)
                            st.success(f"✅ Approved until {expiry_date}")
                            st.rerun()
                    
                    with col_btn2:
                        if st.button(f"❌ Reject", key=f"reject_pending_{idx}"):
                            df_users.at[idx, 'Status'] = 'Rejected'
                            conn.update(worksheet="Sheet1", data=df_users)
                            st.error(f"❌ Request rejected")
                            st.rerun()
                
                st.divider()
    
    # --- TAB 4: ACTIVITY & LOGS ---
    with admin_tabs[3]:
        st.subheader("Activity Logs")
        
        # Display login activity
        if 'Last Login' in df_users.columns and 'Session' in df_users.columns:
            activity_df = df_users[df_users['Session'] == 'Online'][['Name', 'Email', 'Last Login', 'Session']].copy()
            
            if len(activity_df) > 0:
                st.subheader("Currently Online Users")
                st.dataframe(activity_df, use_container_width=True, hide_index=True)
            else:
                st.info("No users currently online")
            
            st.divider()
            
            st.subheader("Login History")
            login_history = df_users[['Name', 'Email', 'Last Login', 'Status']].copy()
            login_history = login_history.sort_values('Last Login', ascending=False, na_position='last')
            st.dataframe(login_history, use_container_width=True, hide_index=True)
        else:
            st.info("Activity logs not available")
    
    # --- TAB 5: SETTINGS ---
    with admin_tabs[4]:
        st.subheader("System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### User Management")
            
            # Bulk approval with duration selector
            st.write("**Bulk Approve Pending Requests:**")
            bulk_duration = st.selectbox(
                "Duration for bulk approval",
                options=[30, 60, 90, 180, 365],
                format_func=lambda x: {30: "30 days", 60: "60 days", 90: "90 days", 180: "6 months", 365: "1 year"}[x],
                key="bulk_duration_select"
            )
            
            if st.button("✅ Approve All Pending"):
                pending_count = len(df_users[df_users['Status'] == 'Pending'])
                if pending_count == 0:
                    st.info("No pending requests to approve")
                else:
                    for idx, user in df_users[df_users['Status'] == 'Pending'].iterrows():
                        df_users.at[idx, 'Status'] = 'Approved'
                        df_users.at[idx, 'Expiry'] = (datetime.datetime.now() + datetime.timedelta(days=bulk_duration)).strftime("%Y-%m-%d")
                    conn.update(worksheet="Sheet1", data=df_users)
                    st.success(f"✅ {pending_count} pending user(s) approved for {bulk_duration} days")
                    st.rerun()
            
            # Cleanup offline users
            if st.button("🧹 Cleanup Offline Sessions"):
                df_users.loc[df_users['Session'] == 'Online', 'Session'] = 'Offline'
                conn.update(worksheet="Sheet1", data=df_users)
                st.success("✅ All sessions reset to offline")
                st.rerun()

        
        with col2:
            st.markdown("### System Info")
            st.metric("Active Users", len(df_users[df_users['Status'] == 'Approved']))
            st.metric("Total Requests", len(df_users))
            st.metric("Rejection Rate", f"{(len(df_users[df_users['Status'] == 'Rejected']) / len(df_users) * 100):.1f}%" if len(df_users) > 0 else "N/A")

def user_dashboard():
    """User Terminal Dashboard"""
    # Load data
    DB_DATA, DB_ERROR = load_local_database()
    
    # Load user's API key on first dashboard entry
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key(st.session_state.user_email)
    
    # Top navigation
    col1, col2, col3 = st.columns([0.8, 0.1, 0.1])
    with col2:
        if st.button("⚙️", help="Settings"):
            st.query_params["page"] = "settings"
    with col3:
        if st.button("🚪", help="Logout"):
            st.session_state.user_verified = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.rerun()
    
    st.title("📟 JDL Intelligence Terminal")
    
    if st.session_state.user_name:
        st.markdown(f"Welcome, **{st.session_state.user_name}** 👋")
    
    df_raw = load_portfolio(st.session_state.user_email)
    current_weights = {'abs': st.session_state.w_abs, 'mom': st.session_state.w_mom, 'div': st.session_state.w_div}
    
    if not df_raw.empty:
        df_raw["Market Chart"] = df_raw["Item Name"].apply(lambda x: f"https://steamdt.com/cs2/{x}")
        pred_res = df_raw.apply(lambda row: get_prediction_metrics(st.session_state.user_email, row, current_weights), axis=1, result_type='expand')
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
                prog = st.progress(0)
                status = st.empty()
                for i, row in df_raw.iterrows():
                    status.text(f"Updating {row['Item Name']}..."); 
                    data, err = fetch_market_data(row["Item Name"], st.session_state.api_key)
                    if data:
                        df_raw.at[i, "Price (CNY)"] = data["price"]
                        df_raw.at[i, "Supply"] = data["supply"]
                        save_history_entry(st.session_state.user_email, row["Item Name"], data["price"], data["supply"], 0)
                    prog.progress((i + 1) / len(df_raw)); 
                    time.sleep(3)
                save_portfolio(st.session_state.user_email, df_raw); 
                st.success("✅ Sync Complete!"); 
                st.rerun()
        
        with st.expander("🔑 API Key Setup"):
            new_key = st.text_input("SteamDT API Key", value=st.session_state.api_key, type="password")
            if st.button("💾 Save Key"): 
                save_api_key(st.session_state.user_email, new_key); 
                st.session_state.api_key = new_key; 
                st.success("✅ Saved!")
        
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
                        save_portfolio(st.session_state.user_email, df_raw); 
                        st.success(f"✅ Added {new_item}"); 
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")
            else:
                st.error(f"❌ {DB_ERROR}")

def main():
    # Show login if not authenticated
    if not st.session_state.user_verified and not st.session_state.admin_verified:
        gatekeeper.show_login(conn)
        return
    
    # Show admin dashboard if admin
    if st.session_state.admin_verified:
        admin_dashboard()
    # Show user dashboard if user
    elif st.session_state.user_verified:
        user_dashboard()

if __name__ == "__main__":
    main()
