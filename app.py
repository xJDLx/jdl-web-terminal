import streamlit as st
import pandas as pd
import os

# --- 1. MASTER ADMIN CONFIGURATION ---
# We now pull the key from Streamlit's secure vault
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    # Fallback if secrets aren't set up yet
    MASTER_ADMIN_KEY = "ADMIN-SETUP-MODE"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 2. THE OWNER GATE ---
if not st.session_state.owner_verified:
    st.title("🔒 JDL Private Terminal")
    st.warning("Restricted Access.")
    
    with st.form("admin_gate"):
        input_key = st.text_input("Master Admin Key", type="password")
        if st.form_submit_button("Authenticate"):
            if input_key == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                st.rerun()
            else:
                st.error("Access Denied.")
    st.stop() 

# --- 3. THE ACTUAL APP ---

def terminal_page():
    st.title("📟 JDL Intelligence Terminal")
    st.success("Admin Session Active")
    
    if os.path.exists("portfolio.csv"):
        df = pd.read_csv("portfolio.csv")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Upload 'portfolio.csv' to your GitHub repo to view data.")

def settings_page():
    st.title("⚙️ System Settings")
    if st.button("Lock Terminal", type="primary"):
        st.session_state.owner_verified = False
        st.rerun()

# --- 4. NAVIGATION ---
pg = st.navigation([
    st.Page(terminal_page, title="Terminal", icon="📟"),
    st.Page(settings_page, title="Settings", icon="⚙️")
])
pg.run()