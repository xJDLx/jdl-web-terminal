import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        email = st.text_input("Member Email").strip().lower()
        if st.button("Access Terminal"):
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            if email in df['Email'].values:
                user = df[df['Email'] == email].iloc[0]
                if str(user['Status']) == "Approved":
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    st.rerun()
                else: st.error("Access Pending Approval.")
            else: st.error("Email not found.")

    with t2:
        st.subheader("New Terminal Request")
        with st.form("req_form", clear_on_submit=True):
            n, e = st.text_input("Name"), st.text_input("Email")
            d = st.number_input("Access Days", min_value=1, value=30)
            if st.form_submit_button("Submit"):
                df = conn.read(worksheet="Sheet1")
                exp = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                new = pd.DataFrame([{"Name":n, "Email":e.lower(), "Date":datetime.now().strftime("%Y-%m-%d"), 
                                     "Status":"Pending", "Last Login":"Never", "Session":"Offline", "Expiry":exp}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new], ignore_index=True))
                st.success("Request sent to Admin.")

    with t3:
        admin_key = st.text_input("Master Key", type="password")
        if st.button("Unlock Admin"):
            if admin_key == st.secrets["MASTER_KEY"]:
                st.session_state.admin_verified = True
                st.rerun()