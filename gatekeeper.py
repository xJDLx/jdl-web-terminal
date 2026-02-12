import streamlit as st
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def show_login(conn):
    st.title("📟 JDL Intelligence System")
    t1, t2, t3 = st.tabs(["Member Login", "Request Access", "Admin Portal"])
    
    with t1:
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password")
        if st.button("Access"):
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            if email in df['Email'].values:
                user = df[df['Email'] == email].iloc[0]
                if str(user['Status']) == "Approved" and hash_password(pwd) == str(user['Password']):
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    # Save to URL for refresh protection
                    st.query_params["role"] = "user"
                    st.query_params["name"] = user['Name']
                    st.rerun()
                else: st.error("Invalid credentials or pending approval.")

    with t3:
        admin_input = st.text_input("Master Key", type="password")
        if st.button("Unlock Admin"):
            if admin_input == st.secrets.get("MASTER_KEY"):
                st.session_state.admin_verified = True
                # Save to URL for refresh protection
                st.query_params["role"] = "admin"
                st.rerun()
            else: st.error("Invalid Key.")