import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
try:
    MASTER_ADMIN_KEY = st.secrets["MASTER_KEY"]
except:
    MASTER_ADMIN_KEY = "jdl2026"

st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# Connect to GSheets (ttl=0 for live tracking)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 2. PERSISTENCE (Refresh Protection) ---
if "admin_auth" in st.query_params and st.query_params["admin_auth"] == MASTER_ADMIN_KEY:
    st.session_state.owner_verified = True

if "owner_verified" not in st.session_state:
    st.session_state.owner_verified = False

# --- 3. THE GATEKEEPER ---
def gatekeeper():
    st.title("📟 JDL Intelligence System")
    tabs = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with tabs[0]:
        st.subheader("Member Access")
        member_key = st.text_input("Enter Access Key", type="password")
        if st.button("Log In"):
            try:
                df = conn.read(worksheet="Sheet1")
                # For this demo, we use the Email as the 'Key'
                if member_key in df['Email'].values:
                    user_data = df[df['Email'] == member_key].iloc[0]
                    expiry = datetime.strptime(str(user_data['Expiry']), "%Y-%m-%d")
                    
                    if user_data['Status'] != "Approved":
                        st.error("Your account is still pending approval.")
                    elif datetime.now() > expiry:
                        st.error(f"Access Expired on {user_data['Expiry']}. Please contact Admin.")
                    else:
                        st.success(f"Welcome, {user_data['Name']}!")
                        # Update Last Login & Session
                        df.loc[df['Email'] == member_key, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        df.loc[df['Email'] == member_key, 'Session'] = "Online"
                        conn.update(worksheet="Sheet1", data=df)
                        st.balloons()
                else:
                    st.error("Invalid Key.")
            except:
                st.error("Database sync error. Ensure columns are correct.")

    with tabs[1]:
        st.subheader("Request Terminal Access")
        with st.form("req_form", clear_on_submit=True):
            n = st.text_input("Name")
            e = st.text_input("Email")
            d = st.number_input("Days Needed", min_value=1, value=30)
            if st.form_submit_button("Submit"):
                df = conn.read(worksheet="Sheet1")
                exp = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                new = pd.DataFrame([{"Name":n,"Email":e,"Date":datetime.now().strftime("%Y-%m-%d"),"Status":"Pending","Last Login":"Never","Session":"Offline","Expiry":exp}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new], ignore_index=True))
                st.success("Sent!")

    with tabs[2]:
        st.subheader("Admin Verification")
        admin_input = st.text_input("Master Key", type="password")
        rem = st.checkbox("Keep me logged in (Persistence)")
        if st.button("Unlock"):
            if admin_input == MASTER_ADMIN_KEY:
                st.session_state.owner_verified = True
                if rem: st.query_params["admin_auth"] = MASTER_ADMIN_KEY
                st.rerun()

# --- 4. MAIN ROUTING ---
if not st.session_state.owner_verified:
    gatekeeper()
    st.stop()

# --- 5. ADMIN DASHBOARD ---
def admin_dashboard():
    st.title("👥 Admin Control Center")
    df = conn.read(worksheet="Sheet1")
    
    # Status Indicators
    st.subheader("User Database")
    st.dataframe(df, use_container_width=True)

    # Access Management
    st.divider()
    target = st.selectbox("Select User", df['Name'].tolist())
    new_days = st.number_input("Update Access (Days from today)", min_value=1, value=30)
    if st.button("Set New Expiry"):
        new_exp = (datetime.now() + timedelta(days=new_days)).strftime("%Y-%m-%d")
        df.loc[df['Name'] == target, 'Expiry'] = new_exp
        conn.update(worksheet="Sheet1", data=df)
        st.success(f"Updated {target} to {new_exp}")
        st.rerun()

pg = st.navigation([
    st.Page(lambda: st.title("📟 Terminal Online"), title="Terminal", icon="📟"),
    st.Page(admin_dashboard, title="Manage Users", icon="👥")
])
pg.run()