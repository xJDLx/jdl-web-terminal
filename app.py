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

# Connect to GSheets (No caching for live tracking)
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
                # Update Admin's own status to Online
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
        
        if not df.empty:
            # Formatting the table for better visibility
            def color_status(val):
                color = 'green' if val == "Online" else 'red'
                return f'color: {color}'

            st.subheader("Live User Logs")
            st.dataframe(df.style.applymap(color_status, subset=['Session']), use_container_width=True)
            
            # Approve/Deny Actions
            st.divider()
            st.subheader("Manage Requests")
            col1, col2 = st.columns(2)
            with col1:
                user_to_mod = st.selectbox("Select User", df['Name'].tolist())
            with col2:
                new_status = st.radio("Set Status", ["Approved", "Pending", "Denied"], horizontal=True)
            
            if st.button("Update User Status"):
                df.loc[df['Name'] == user_to_mod, 'Status'] = new_status
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"Updated {user_to_mod} to {new_status}")
                st.rerun()

        else:
            st.warning("No data found in Sheet1.")
            
    except Exception as e:
        st.error("Data Sync Error")
        st.exception(e)

pg = st.navigation([
    st.Page(lambda: st.title("📟 Terminal Online"), title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥")
])
pg.run()