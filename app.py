import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime, date

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# --- 2. SECURITY & STATE INITIALIZATION ---
# BEST PRACTICE: Store keys with their expiration date (YYYY, MM, DD)
VALID_MEMBERSHIP_KEYS = {
    "JDL-ALPHA-2026": date(2026, 3, 1),   # Expires March 1st, 2026
    "JDL-TRIAL-7DAYS": date(2026, 2, 20), # Short-term access
    "MEMBER-FOREVER": date(2099, 1, 1)    # Long-term access
}

if "membership_verified" not in st.session_state:
    st.session_state.membership_verified = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 3. ACCESS CONTROL PAGES ---

def membership_gate():
    st.title("📟 JDL Access Portal")
    st.info("Verification Required")
    
    with st.form("membership_form"):
        entered_key = st.text_input("Enter Membership Key", type="password")
        if st.form_submit_button("Verify Key"):
            # Check if key exists
            if entered_key in VALID_MEMBERSHIP_KEYS:
                expiry_date = VALID_MEMBERSHIP_KEYS[entered_key]
                # Check if today is before the expiry date
                if date.today() <= expiry_date:
                    st.session_state.membership_verified = True
                    st.success(f"Key Verified! Access valid until {expiry_date}")
                    st.rerun()
                else:
                    st.error(f"This key expired on {expiry_date}. Please contact JDL.")
            else:
                st.error("Invalid Key. Access Denied.")

def login_page():
    st.title("🔒 JDL Secure Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Access Terminal"):
            if username == "admin" and password == "jdl2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

def logout():
    for key in ["membership_verified", "logged_in", "api_key"]:
        st.session_state[key] = "" if key == "api_key" else False
    st.rerun()

# --- 4. APP CONTENT ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    if not st.session_state.api_key:
        st.warning("⚠️ API Key Missing: Go to Settings.")
        return
    
    st.success("✅ System Online")
    CSV_FILE = "portfolio.csv"
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Waiting for 'portfolio.csv' data...")

def settings_page():
    st.title("⚙️ Settings")
    st.session_state.api_key = st.text_input("Private API Key", type="password", value=st.session_state.api_key)
    if st.button("Full System Logout", type="primary"):
        logout()

# --- 5. MAIN NAVIGATION LOGIC ---

if not st.session_state.membership_verified:
    membership_gate()
elif not st.session_state.logged_in:
    login_page()
else:
    st.sidebar.button("Logout", on_click=logout)
    pg = st.navigation([
        st.Page(terminal_page, title="Terminal", icon="📟"),
        st.Page(settings_page, title="Settings", icon="⚙️")
    ])
    pg.run()