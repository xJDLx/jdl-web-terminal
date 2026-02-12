import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIAL CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "jdl2026"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Connect with TTL=0 for live tracking
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 2. PERSISTENCE (REFRESH PROTECTION) ---
if "admin_auth" in st.query_params and st.query_params["admin_auth"] == MASTER_ADMIN_KEY:
    st.session_state.owner_verified = True

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 3. PAGE FUNCTIONS (Replaces Lambdas) ---

def terminal_online():
    st.title("📟 Terminal Online")
    st.success("System operational. Welcome back, Admin.")

def logout_page():
    st.title("🔒 Logging out...")
    st.query_params.clear() # Clears the persistence key
    st.session_state.owner_verified = False
    st.rerun()

def admin_dashboard():
    st.title("👥 User & Session Management")
    
    # Manual Refresh
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear() # Clears internal cache
        st.rerun()

    try:
        df = conn.read(worksheet="Sheet1")
        st.subheader("User Database")
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Quick Actions")
        if not df.empty:
            target = st.selectbox("Select User", df['Name'].tolist())
            new_stat = st.radio("Set Status", ["Approved", "Denied", "Pending"], horizontal=True)
            if st.button("Update Status"):
                df.loc[df['Name'] == target, 'Status'] = new_stat
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"Updated {target} to {new_stat}")
                st.rerun()
    except Exception as e:
        st.error("Sync Error: Ensure 'Sheet1' has all 7 required columns.")

# --- 4. THE GATEKEEPER (LOGIN) ---
def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with tabs[0]: # MEMBER LOGIN
        st.subheader("Member Access")
        member_key = st.text_input("Enter Email", placeholder="your@email.com").strip().lower()
        if st.button("Log In"):
            try:
                df = conn.read(worksheet="Sheet1")
                df['Email'] = df['Email'].str.strip().str.lower()
                if member_key in df['Email'].values:
                    user = df[df['Email'] == member_key].iloc[0]
                    expiry = datetime.strptime(str(user['Expiry']), "%Y-%m-%d")
                    if user['Status'] != "Approved":
                        st.error("Access Pending: Approval required.")
                    elif datetime.now() > expiry:
                        st.error(f"Access Expired on {user['Expiry']}.")
                    else:
                        st.success(f"Welcome, {user['Name']}!")
                        df.loc[df['Email'] == member_key, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        df.loc[df['Email'] == member_key, 'Session'] = "Online"
                        conn.update(worksheet="Sheet1", data=df)
                        st.balloons()
                else: st.error("Email not found.")
            except: st.error("Database Error. Check headers.")

    with tabs[1]: # REQUEST ACCESS
        st.subheader("New Terminal Request")
        with st.form("req_form", clear_on_submit=True):
            n, e = st.text_input("Full Name"), st.text_input("Email")
            d = st.number_input("Days Needed", min_value=1, value=30)
            if st.form_submit_button("Submit"):
                df = conn.read(worksheet="Sheet1")
                exp = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                new = pd.DataFrame([{"Name":n, "Email":e.lower(), "Date":datetime.now().strftime("%Y-%m-%d"), 
                                     "Status":"Pending", "Last Login":"Never", "Session":"Offline", "Expiry":exp}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new], ignore_index=True))
                st.success("Request sent!")

    with tabs[2]: # ADMIN LOGIN
        st.subheader("Admin Control")
        admin_input = st.text_input("Master Key", type="password")
        rem = st.checkbox("Keep me logged in (Refresh Protection)")
        if st.button("Unlock Admin"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                if rem: st.query_params["admin_auth"] = MASTER_ADMIN_KEY
                st.rerun()

# --- 5. NAVIGATION LOGIC ---
if not st.session_state.owner_verified:
    gatekeeper()
else:
    # Use named functions instead of lambdas to prevent StreamlitAPIException
    pg = st.navigation([
        st.Page(terminal_online, title="Terminal", icon="📟"),
        st.Page(admin_dashboard, title="Manage Users", icon="👥"),
        st.Page(logout_page, title="Logout", icon="🔒")
    ])
    pg.run()