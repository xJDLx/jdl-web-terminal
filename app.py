import streamlit as st
import pandas as pd
import os
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Safe Connection Attempt
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ Connection Error: Check your Streamlit Secrets.")
    st.info("Make sure you have [connections.gsheets] and 'spreadsheet' defined.")
    st.stop()

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 2. THE GATEKEEPER ---

def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Login", "Request Access", "Admin Portal"])
    
    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("request_form", clear_on_submit=True):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Email Address")
            if st.form_submit_button("Submit Request"):
                if req_name and req_email:
                    try:
                        # Append data to Google Sheets
                        existing_data = conn.read()
                        new_row = pd.DataFrame([{"Name": req_name, "Email": req_email, "Date": str(date.today())}])
                        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                        conn.update(data=updated_df)
                        st.success("Request saved permanently to Google Sheets!")
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
                else:
                    st.error("Please fill in all fields.")

    with tabs[2]:
        st.subheader("Admin Verification")
        admin_input = st.text_input("Master Admin Key", type="password")
        if st.button("Unlock Admin"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                st.rerun()

# --- 3. MAIN ROUTING ---
if not st.session_state.owner_verified:
    gatekeeper()
    st.stop()

# --- 4. ADMIN PAGES ---
def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    st.success("Admin Session Active")

def admin_dashboard():
    st.title("👥 User Administration")
    try:
        df = conn.read()
        st.dataframe(df, use_container_width=True)
    except:
        st.error("Could not load requests from Google Sheets.")

pg = st.navigation([
    st.Page(terminal_page, title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥")
])
pg.run()