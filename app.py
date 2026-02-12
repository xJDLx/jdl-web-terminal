import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import date

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# --- 2. SECURITY & STATE INITIALIZATION ---
# Add your generated keys here
VALID_MEMBERSHIP_KEYS = {
    "JDL-ALPHA-2026": date(2026, 3, 1),   
    "k9P2mX7LqW1z": date(2026, 5, 12),  # Randomly generated key
    "v8N4jR3TkP9s": date(2026, 2, 28)   # Randomly generated key
}

if "membership_verified" not in st.session_state:
    st.session_state.membership_verified = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- 3. ACCESS CONTROL ---

def membership_gate():
    st.title("📟 JDL Access Portal")
    with st.form("membership_form"):
        entered_key = st.text_input("Enter Membership Key", type="password")
        if st.form_submit_button("Verify Key"):
            if entered_key in VALID_MEMBERSHIP_KEYS:
                if date.today() <= VALID_MEMBERSHIP_KEYS[entered_key]:
                    st.session_state.membership_verified = True
                    st.rerun()
                else:
                    st.error("Key Expired.")
            else:
                st.error("Invalid Key.")

def login_page():
    st.title("🔒 JDL Secure Login")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Access Terminal"):
            if u == "admin" and p == "jdl2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

# --- 4. APP PAGES ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    if not st.session_state.api_key:
        st.warning("⚠️ API Key Missing: Go to Settings.")
        return
    st.success("✅ System Online")
    
    if os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Awaiting portfolio.csv...")

def settings_page():
    st.title("⚙️ Settings")
    st.session_state.api_key = st.text_input("Private API Key", type="password", value=st.session_state.api_key)
    if st.button("Logout", type="primary"):
        st.session_state.membership_verified = False
        st.session_state.logged_in = False
        st.rerun()

# --- 5. RUN NAVIGATION ---

if not st.session_state.membership_verified:
    membership_gate()
elif not st.session_state.logged_in:
    login_page()
else:
    pg = st.navigation([
        st.Page(terminal_page, title="Terminal", icon="📟"),
        st.Page(settings_page, title="Settings", icon="⚙️")
    ])
    pg.run()