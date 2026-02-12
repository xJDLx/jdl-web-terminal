import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Helper function to hash passwords so you can't see them
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        email = st.text_input("Email").strip().lower()
        # type="password" masks the input
        pwd = st.text_input("Password", type="password") 
        if st.button("Access"):
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            
            if email in df['Email'].values:
                user = df[df['Email'] == email].iloc[0]
                # Compare the entered password's hash with the stored hash
                if user['Status'] == "Approved" and hash_password(pwd) == user['Password']:
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    st.rerun()
                elif user['Status'] != "Approved":
                    st.error("Access Pending.")
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("Email not found.")

    with t2:
        st.subheader("Request Terminal Access")
        with st.form("req_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            e = st.text_input("Email").strip().lower()
            p = st.text_input("Create Password", type="password", help="I cannot see this.")
            if st.form_submit_button("Submit Request"):
                df = conn.read(worksheet="Sheet1")
                # We save a default Expiry that the Admin will change
                new_data = pd.DataFrame([{
                    "Name": n, "Email": e, "Password": hash_password(p),
                    "Date": datetime.now().strftime("%Y-%m-%d"), 
                    "Status": "Pending", "Expiry": "2026-01-01" 
                }])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new_data], ignore_index=True))
                st.success("Request sent. Admin will set your access duration.")

    # (Admin Portal code remains same...)