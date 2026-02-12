import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "jdl2026"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Connect to GSheets
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
                        df = conn.read(worksheet="Sheet1")
                        new_row = pd.DataFrame([{
                            "Name": req_name, 
                            "Email": req_email, 
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Status": "Pending",
                            "Last Login": "Never",
                            "Session": "Offline"
                        }])
                        updated_df = pd.concat([df, new_row], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.success("✅ Request sent! Admin will review.")
                    except Exception as e:
                        st.error(f"Error: {e}")

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

# --- 4. ADMIN DASHBOARD ---
def admin_dashboard():
    st.title("👥 User & Session Management")
    
    try:
        df = conn.read(worksheet="Sheet1")
        
        # SAFETY CHECK: Ensure the 'Session' column exists before styling
        if 'Session' in df.columns:
            def color_status(val):
                color = 'green' if val == "Online" else 'red'
                return f'color: {color}'

            st.subheader("Live User Logs")
            st.dataframe(df.style.map(color_status, subset=['Session']), use_container_width=True)
        else:
            st.error("❌ Missing Columns!")
            st.warning("Please add 'Status', 'Last Login', and 'Session' as headers in Row 1 of your Google Sheet.")
            st.dataframe(df) # Show raw data so you can see what's missing

        # Management Tools
        if not df.empty and 'Name' in df.columns:
            st.divider()
            user_to_mod = st.selectbox("Select User to Update", df['Name'].tolist())
            new_status = st.radio("New Status", ["Approved", "Pending", "Denied"], horizontal=True)
            
            if st.button("Update Database"):
                df.loc[df['Name'] == user_to_mod, 'Status'] = new_status
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"Updated {user_to_mod}!")
                st.rerun()
            
    except Exception as e:
        st.error("Data Sync Error")
        st.exception(e)

pg = st.navigation([
    st.Page(lambda: st.title("📟 Terminal Online"), title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥")
])
pg.run()