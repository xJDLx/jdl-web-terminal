import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "jdl2026"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Connect to GSheets
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 2. PERSISTENCE LOGIC (The "No Logout" Hack) ---
# We use a query parameter to "remember" the admin between refreshes
query_params = st.query_params
if "admin_auth" in query_params and query_params["admin_auth"] == MASTER_ADMIN_KEY:
    st.session_state.owner_verified = True

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 3. THE GATEKEEPER ---
def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Login", "Request Access", "Admin Portal"])
    
    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("request_form", clear_on_submit=True):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Email Address")
            days_requested = st.number_input("Days of Access Needed", min_value=1, max_value=365, value=30)
            
            if st.form_submit_button("Submit Request"):
                if req_name and req_email:
                    try:
                        df = conn.read(worksheet="Sheet1")
                        # Calculate future expiry
                        expiry_date = (datetime.now() + timedelta(days=days_requested)).strftime("%Y-%m-%d")
                        
                        new_row = pd.DataFrame([{
                            "Name": req_name, 
                            "Email": req_email, 
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Status": "Pending",
                            "Last Login": "Never",
                            "Session": "Offline",
                            "Expiry": expiry_date
                        }])
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.success(f"✅ Request sent for {days_requested} days!")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tabs[2]:
        st.subheader("Admin Verification")
        admin_input = st.text_input("Master Admin Key", type="password")
        remember_me = st.checkbox("Keep me logged in (Stay logged in after refresh)")
        
        if st.button("Unlock Admin"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                if remember_me:
                    st.query_params["admin_auth"] = MASTER_ADMIN_KEY
                st.rerun()

# --- 4. MAIN ROUTING ---
if not st.session_state.owner_verified:
    gatekeeper()
    st.stop()

# --- 5. ADMIN DASHBOARD ---
def admin_dashboard():
    st.title("👥 User & Expiry Management")
    
    try:
        df = conn.read(worksheet="Sheet1")
        
        if 'Expiry' in df.columns:
            # Highlight expired users in red
            def highlight_expiry(row):
                try:
                    expiry = datetime.strptime(str(row['Expiry']), "%Y-%m-%d")
                    if expiry < datetime.now():
                        return ['background-color: #ffcccc'] * len(row)
                except:
                    pass
                return [''] * len(row)

            st.subheader("User Database")
            st.dataframe(df.style.apply(highlight_expiry, axis=1), use_container_width=True)
        else:
            st.error("Missing 'Expiry' column in Google Sheet!")

        # Edit Access Length
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            user_to_edit = st.selectbox("Select User", df['Name'].tolist())
        with col2:
            new_days = st.number_input("Extend/Set Access (Days from today)", min_value=1, value=30)

        if st.button("Update Access Length"):
            new_expiry = (datetime.now() + timedelta(days=new_days)).strftime("%Y-%m-%d")
            df.loc[df['Name'] == user_to_edit, 'Expiry'] = new_expiry
            conn.update(worksheet="Sheet1", data=df)
            st.success(f"Access for {user_to_edit} updated to {new_expiry}")
            st.rerun()

    except Exception as e:
        st.error("Data Sync Error")
        st.exception(e)

def logout():
    st.query_params.clear()
    st.session_state.owner_verified = False
    st.rerun()

pg = st.navigation([
    st.Page(lambda: st.title("📟 Terminal Online"), title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥"),
    st.Page(logout, title="Logout", icon="🔒")
])
pg.run()