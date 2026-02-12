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
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password") 
        if st.button("Access Terminal"):
            df = conn.read(worksheet="Sheet1", ttl=0)
            df['Email'] = df['Email'].str.strip().str.lower()
            
            if email in df['Email'].values:
                # Find the row index for this user
                idx = df[df['Email'] == email].index[0]
                user = df.iloc[idx]
                
                if str(user['Status']) == "Approved" and hash_password(pwd) == str(user['Password']):
                    # --- CRITICAL: UPDATE STATUS TO ONLINE ---
                    df.at[idx, 'Session'] = "Online"
                    df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.update(worksheet="Sheet1", data=df)
                    
                    # Set Session State
                    st.session_state.user_verified = True
                    st.session_state.user_name = user['Name']
                    st.query_params["role"] = "user"
                    st.query_params["name"] = user['Name']
                    st.rerun()
                elif str(user['Status']) != "Approved":
                    st.error("Status: " + str(user['Status']))
                else:
                    st.error("Incorrect Password.")
            else:
                st.error("User not found.")

    # ... (Keep T2 and T3 the same) ...