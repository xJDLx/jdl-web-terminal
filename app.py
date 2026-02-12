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
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0) #

# Initialize Session States
if "admin_verified" not in st.session_state:
    st.session_state.admin_verified = False
if "user_verified" not in st.session_state:
    st.session_state.user_verified = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# --- 2. PERSISTENCE (REFRESH PROTECTION) ---
if "admin_auth" in st.query_params and st.query_params["admin_auth"] == MASTER_ADMIN_KEY:
    st.session_state.admin_verified = True #

# --- 3. PAGE CONTENT FUNCTIONS ---

def member_home():
    st.title(f"📟 Welcome, {st.session_state.user_name}")
    st.success("Authorized Access Granted.")
    st.info("This is your Member Dashboard.")
    
    # Add your member-only content here
    st.write("Current Intelligence Feeds...")
    
    if st.button("Logout"):
        st.session_state.user_verified = False
        st.rerun()

def admin_dashboard():
    st.title("👥 User & Session Management")
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear() #
        st.rerun()

    try:
        df = conn.read(worksheet="Sheet1")
        st.subheader("User Database")
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Update User Status")
        if not df.empty:
            target = st.selectbox("Select User", df['Name'].tolist())
            new_stat = st.radio("Status", ["Approved", "Denied", "Pending"], horizontal=True)
            if st.button("Update"):
                df.loc[df['Name'] == target, 'Status'] = new_stat
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"Set {target} to {new_stat}")
                st.rerun()
    except:
        st.error("Sync Error: Check Spreadsheet columns.")

# --- 4. THE GATEKEEPER (LOGIN TABS) ---
def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with tabs[0]: # MEMBER LOGIN
        st.subheader("Member Access")
        email_input = st.text_input("Enter Email", placeholder="your@email.com").strip().lower()
        if st.button("Access Terminal"):
            try:
                df = conn.read(worksheet="Sheet1", ttl=0) # Forced refresh
                df['Email'] = df['Email'].str.strip().str.lower()
                
                if email_input in df['Email'].values:
                    user = df[df['Email'] == email_input].iloc[0]
                    expiry = datetime.strptime(str(user['Expiry']), "%Y-%m-%d")
                    
                    if str(user['Status']).strip() != "Approved":
                        st.error("Access Pending: Admin approval required.")
                    elif datetime.now() > expiry:
                        st.error(f"Access Expired on {user['Expiry']}.")
                    else:
                        # Log them in and update state
                        st.session_state.user_verified = True
                        st.session_state.user_name = user['Name']
                        
                        # Update Live Sheet
                        df.loc[df['Email'] == email_input, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        df.loc[df['Email'] == email_input, 'Session'] = "Online"
                        conn.update(worksheet="Sheet1", data=df)
                        st.rerun() # Redirects to Home Page
                else:
                    st.error("Email not found.")
            except Exception as e:
                st.error("Database connection failed.")

    with tabs[1]: # REQUEST ACCESS
        st.subheader("New Request")
        with st.form("req", clear_on_submit=True):
            n, e = st.text_input("Name"), st.text_input("Email")
            d = st.number_input("Days", min_value=1, value=30)
            if st.form_submit_button("Submit"):
                df = conn.read(worksheet="Sheet1")
                exp = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                new = pd.DataFrame([{"Name":n, "Email":e.lower(), "Date":datetime.now().strftime("%Y-%m-%d"), 
                                     "Status":"Pending", "Last Login":"Never", "Session":"Offline", "Expiry":exp}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new], ignore_index=True))
                st.success("Sent!")

    with tabs[2]: # ADMIN LOGIN
        st.subheader("Admin Control")
        admin_input = st.text_input("Master Key", type="password")
        rem = st.checkbox("Keep me logged in")
        if st.button("Unlock Admin"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.admin_verified = True
                if rem: st.query_params["admin_auth"] = MASTER_ADMIN_KEY
                st.rerun()

# --- 5. MAIN ROUTING LOGIC ---
if st.session_state.admin_verified:
    # If Admin is logged in, show Admin Pages
    pg = st.navigation([
        st.Page(admin_dashboard, title="Manage Users", icon="👥"),
        st.Page(lambda: (st.query_params.clear(), st.session_state.update({"admin_verified": False}), st.rerun()), title="Logout", icon="🔒")
    ])
    pg.run()
elif st.session_state.user_verified:
    # If User is logged in, show Member Home
    member_home()
else:
    # Otherwise, show the Login Gatekeeper
    gatekeeper()