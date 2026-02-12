import streamlit as st
import pandas as pd
from datetime import datetime

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        email = st.text_input("Email").strip().lower()
        remember = st.checkbox("Keep me logged in")
        if st.button("Access"):
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            
            if email in df['Email'].values:
                user = df[df['Email'] == email].iloc[0]
                if str(user['Status']) == "Approved":
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    if remember:
                        st.query_params["u"] = email
                    st.rerun()
                else:
                    st.error("Access Pending.")
            else:
                st.error("Email not found.")
    
    with t3:
        admin_key = st.text_input("Master Key", type="password")
        if st.button("Unlock Admin"):
            if admin_key == st.secrets.get("MASTER_KEY"):
                st.session_state.admin_verified = True
                st.rerun()
            else:
                st.error("Invalid Key.")