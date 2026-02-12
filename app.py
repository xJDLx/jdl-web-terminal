import streamlit as st
import pandas as pd
import os
from datetime import date

# --- 1. MASTER ADMIN CONFIGURATION ---
# ONLY YOU should know this key.
MASTER_ADMIN_KEY = "JDL-OWNER-99X-2026" 

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Initialize the owner session state
if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 2. THE OWNER GATE ---
if not st.session_state.owner_verified:
    st.title("🔒 JDL Private Terminal")
    st.warning("This system is restricted to authorized personnel only.")
    
    with st.form("admin_gate"):
        input_key = st.text_input("Master Admin Key", type="password")
        if st.form_submit_button("Authenticate"):
            if input_key == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                st.rerun()
            else:
                st.error("Unauthorized access attempt recorded.")
    st.stop() # This stops the rest of the code from running until verified

# --- 3. THE ACTUAL APP (Only visible to YOU) ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    st.success("Welcome back, Admin.")
    
    if os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Upload 'portfolio.csv' to see your data.")

def settings_page():
    st.title("⚙️ System Settings")
    st.write("You have full control over the terminal.")
    
    if st.button("Lock Terminal", type="primary"):
        st.session_state.owner_verified = False
        st.rerun()

# --- 4. NAVIGATION ---
pg = st.navigation([
    st.Page(terminal_page, title="Terminal", icon="📟"),
    st.Page(settings_page, title="Settings", icon="⚙️")
])
pg.run()