import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "jdl2026"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# We use ttl=0 to bypass all caching and get live data
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

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
                        # We specify worksheet="Sheet1" to be safe
                        df = conn.read(worksheet="Sheet1")
                        new_row = pd.DataFrame([{"Name": req_name, "Email": req_email, "Date": str(date.today())}])
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.success("✅ Request saved to Google Sheets!")
                    except Exception as e:
                        st.error(f"Error saving: {e}")
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
def admin_dashboard():
    st.title("👥 User Administration")
    
    # Check if headers exist in the sheet
    st.info("Attempting to fetch data from 'Sheet1'...")

    try:
        # Explicitly naming the worksheet handles sync issues
        df = conn.read(worksheet="Sheet1")
        
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("The connection is active, but the sheet appears to be empty or formatted incorrectly.")
            st.write("Ensure your first row has: **Name**, **Email**, **Date**")
            
    except Exception as e:
        st.error("❌ Data Sync Error")
        st.exception(e)

pg = st.navigation([
    st.Page(lambda: st.title("📟 Terminal Online"), title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥")
])
pg.run()