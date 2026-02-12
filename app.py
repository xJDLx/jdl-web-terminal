import streamlit as st
import pandas as pd
import os
import secrets
import string
from datetime import date, timedelta

# --- 1. MASTER CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Initialize session states
if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 2. THE MASTER GATE (FOR YOU ONLY) ---
if not st.session_state.owner_verified:
    st.title("🔒 JDL Private Terminal")
    with st.form("admin_gate"):
        input_key = st.text_input("Master Admin Key", type="password")
        if st.form_submit_button("Authenticate"):
            if input_key == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                st.rerun()
            else:
                st.error("Access Denied.")
    st.stop() 

# --- 3. PAGE FUNCTIONS ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    st.success("Admin Session Active")
    
    if os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Upload 'portfolio.csv' to view data.")

def user_management_page():
    st.title("👥 User & Key Management")
    st.write("Generate access keys for clients or temporary users.")

    with st.expander("➕ Create New Access Key", expanded=True):
        new_username = st.text_input("Client/User Name", placeholder="e.g. John Doe")
        days_valid = st.number_input("Days of Access", min_value=1, max_value=365, value=30)
        
        if st.button("Generate & Format Key"):
            if new_username:
                # Generate random 12-char key
                alphabet = string.ascii_letters + string.digits
                generated_key = ''.join(secrets.choice(alphabet) for i in range(12))
                expiry_date = date.today() + timedelta(days=days_valid)
                
                st.subheader("Generated Entry for app.py")
                st.info(f"User: {new_username} | Expires: {expiry_date}")
                
                # This provides the exact code to copy into your VALID_MEMBERSHIP_KEYS
                code_snippet = f'"{generated_key}": date({expiry_date.year}, {expiry_date.month}, {expiry_date.day}), # {new_username}'
                st.code(code_snippet, language="python")
                st.warning("Copy the line above into the 'VALID_MEMBERSHIP_KEYS' section of your code.")
            else:
                st.error("Please enter a Username first.")

def settings_page():
    st.title("⚙️ System Settings")
    if st.button("Lock Terminal", type="primary"):
        st.session_state.owner_verified = False
        st.rerun()

# --- 4. NAVIGATION ---
pg = st.navigation([
    st.Page(terminal_page, title="Terminal", icon="📟"),
    st.Page(user_management_page, title="User Management", icon="👥"),
    st.Page(settings_page, title="Settings", icon="⚙️")
])
pg.run()