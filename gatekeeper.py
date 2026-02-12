import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        st.subheader("Member Access")
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password") 
        if st.button("Access Terminal"):
            # Pull fresh data to check credentials
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            
            if email in df['Email'].values:
                user_idx = df[df['Email'] == email].index[0]
                user = df.iloc[user_idx]
                
                if str(user['Status']) == "Approved" and hash_password(pwd) == str(user['Password']):
                    # --- LIVE STATUS UPDATE ---
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    df.at[user_idx, 'Last Login'] = now
                    df.at[user_idx, 'Session'] = "Online"
                    
                    # Push the update to Google Sheets immediately
                    conn.update(worksheet="Sheet1", data=df)
                    
                    # Set Session States
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    st.query_params["role"] = "user"
                    st.query_params["name"] = user['Name']
                    st.rerun()
                elif str(user['Status']) != "Approved":
                    st.error("Access Pending Approval.")
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("Email not found.")

    with t2: # REQUEST ACCESS
        st.subheader("New Terminal Request")
        with st.form("req_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            e = st.text_input("Email Address").strip().lower()
            p = st.text_input("Create Private Password", type="password")
            if st.form_submit_button("Submit Request"):
                if n and e and p:
                    df = conn.read(worksheet="Sheet1", ttl=0)
                    new_data = pd.DataFrame([{
                        "Name": n, "Email": e, "Password": hash_password(p),
                        "Date": datetime.now().strftime("%Y-%m-%d"), 
                        "Status": "Pending", "Expiry": "Pending Admin",
                        "Last Login": "Never", "Session": "Offline"
                    }])
                    conn.update(worksheet="Sheet1", data=pd.concat([df, new_data], ignore_index=True))
                    st.success("Request sent!")

    with t3: # ADMIN PORTAL
        st.subheader("System Administration")
        admin_key = st.text_input("Master Key", type="password")
        if st.button("Unlock Admin"):
            if admin_key == st.secrets.get("MASTER_KEY"):
                st.session_state.admin_verified = True
                st.query_params["role"] = "admin"
                st.rerun()
            else: st.error("Invalid Master Key.")