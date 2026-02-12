import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Initialize session states
if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Login"

# --- 2. THE GATEKEEPER LOGIC ---

def gatekeeper():
    st.title("📟 JDL Intelligence System")
    
    tabs = st.tabs(["Login", "Request Access", "Admin Portal"])
    
    with tabs[0]:
        st.subheader("Member Login")
        user_key = st.text_input("Enter your Access Key", type="password", key="user_login")
        if st.button("Access Terminal"):
            # This is where we will check the 'Database' later
            st.error("Access Keys are currently being migrated. Please contact Admin.")

    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("request_form"):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Email Address")
            reason = st.text_area("Reason for Access")
            if st.form_submit_button("Submit Request"):
                # Placeholder for sending to Google Sheets
                st.success(f"Thank you {req_name}. Your request has been sent to JDL Intelligence.")
                st.info("You will receive your access key via email once approved.")

    with tabs[2]:
        st.subheader("Admin Verification")
        admin_input = st.text_input("Master Admin Key", type="password", key="admin_login")
        if st.button("Unlock Admin"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                st.rerun()
            else:
                st.error("Invalid Master Key.")

# --- 3. MAIN APP ROUTING ---

if not st.session_state.owner_verified:
    gatekeeper()
    st.stop()

# --- 4. THE ACTUAL APP (Only for YOU) ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    st.success("Admin Session Active")
    if os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Awaiting portfolio.csv...")

def admin_dashboard():
    st.title("👥 User Administration")
    st.write("Current Pending Requests:")
    # Later, this will pull from Google Sheets
    st.write("*(No pending requests)*")

def settings_page():
    st.title("⚙️ System Settings")
    if st.button("Lock Terminal", type="primary"):
        st.session_state.owner_verified = False
        st.rerun()

# --- 5. NAVIGATION ---
pg = st.navigation([
    st.Page(terminal_page, title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥"),
    st.Page(settings_page, title="Settings", icon="⚙️")
])
pg.run()