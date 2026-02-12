import streamlit as st
import pandas as pd
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# --- 2. SECURITY & STATE INITIALIZATION ---
VALID_MEMBERSHIP_KEYS = ["JDL-ALPHA-2026", "JDL-BETA-99"]

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
            if entered_key in VALID_MEMBERSHIP_KEYS:
                st.session_state.membership_verified = True
                st.rerun()
            else:
                st.error("Invalid Key.")

def login_page():
    st.title("🔒 JDL Secure Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Access Terminal"):
            # Use these to log in
            if username == "admin" and password == "jdl2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

def logout():
    st.session_state.membership_verified = False
    st.session_state.logged_in = False
    st.session_state.api_key = ""
    st.rerun()

# --- 4. APP CONTENT ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    if not st.session_state.api_key:
        st.warning("⚠️ API Key Missing: Go to Settings to unlock.")
        return
    
    st.success("✅ System Online")
    # Search for a CSV in the current folder
    CSV_FILE = "portfolio.csv"
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("To see data, upload 'portfolio.csv' to your GitHub folder.")

def settings_page():
    st.title("⚙️ Terminal Settings")
    st.subheader("🔑 API Configuration")
    st.session_state.api_key = st.text_input("Private API Key", type="password", value=st.session_state.api_key)
    
    st.divider()
    if st.button("Full System Logout", type="primary"):
        logout()

# --- 5. MAIN NAVIGATION LOGIC ---

if not st.session_state.membership_verified:
    membership_gate()
elif not st.session_state.logged_in:
    login_page()
else:
    # This creates the sidebar menu
    pg = st.navigation([
        st.Page(terminal_page, title="Terminal", icon="📟"),
        st.Page(settings_page, title="Settings", icon="⚙️")
    ])
    pg.run()