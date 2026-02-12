import streamlit as st
import pandas as pd
import os
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION & DATABASE CONNECTION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 2. THE GATEKEEPER ---

def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Login", "Request Access", "Admin Portal"])
    
    with tabs[0]:
        st.subheader("Member Login")
        user_key = st.text_input("Enter Access Key", type="password")
        if st.button("Access Terminal"):
            st.error("Key verification is currently offline.")

    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("request_form", clear_on_submit=True):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Email Address")
            if st.form_submit_button("Submit Request"):
                if req_name and req_email:
                    # PERMANENT SAVING:
                    # 1. Read existing data
                    existing_data = conn.read(worksheet="Sheet1", usecols=[0,1,2])
                    # 2. Add new row
                    new_row = pd.DataFrame([{"Name": req_name, "Email": req_email, "Date": str(date.today())}])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    # 3. Write back to sheet
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.success("Request saved permanently! Admin will review soon.")
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

def admin_dashboard():
    st.title("👥 User Administration")
    st.subheader("Live Pending Requests (from Google Sheets)")
    
    try:
        # Pull live data from the sheet
        df = conn.read(worksheet="Sheet1")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            if st.button("Refresh Data"):
                st.rerun()
        else:
            st.info("No requests found in the sheet.")
    except:
        st.error("Could not connect to Google Sheets. Check your Secrets.")

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