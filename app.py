import streamlit as st
import pandas as pd
import os
from datetime import date

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Initialize persistent memory for the current session
if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False
if "pending_requests" not in st.session_state:
    st.session_state.pending_requests = []

# --- 2. THE GATEKEEPER ---

def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Login", "Request Access", "Admin Portal"])
    
    with tabs[0]:
        st.subheader("Member Login")
        user_key = st.text_input("Enter your Access Key", type="password")
        if st.button("Access Terminal"):
            st.error("Invalid or Expired Key.")

    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("request_form", clear_on_submit=True):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Email Address")
            if st.form_submit_button("Submit Request"):
                if req_name and req_email:
                    # Save request to the session list
                    new_req = {"Name": req_name, "Email": req_email, "Date": str(date.today())}
                    st.session_state.pending_requests.append(new_req)
                    st.success(f"Request sent! Admin will review your access.")
                else:
                    st.error("Please fill in all fields.")

    with tabs[2]:
        st.subheader("Admin Verification")
        admin_input = st.text_input("Master Admin Key", type="password")
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

# --- 4. THE ACTUAL APP ---

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
    st.subheader("Current Pending Requests")
    
    if st.session_state.pending_requests:
        # Convert the list of requests into a table
        req_df = pd.DataFrame(st.session_state.pending_requests)
        st.table(req_df)
        if st.button("Clear All Requests"):
            st.session_state.pending_requests = []
            st.rerun()
    else:
        st.info("No pending requests at this time.")

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