import streamlit as st
from datetime import datetime
import pandas as pd

def show_home(conn):
    # 1. SETUP USER IDENTITY
    name = st.session_state.get("user_name", "Member")
    # Retrieve email from URL to identify the user in the sheet
    email = st.query_params.get("u") 
    
    # 2. THE HEARTBEAT (Forces "Online" Status)
    # We use a session flag so we don't spam the API on every single interaction
    if "status_checked" not in st.session_state:
        if email:
            try:
                # Read the sheet to find the user
                df = conn.read(worksheet="Sheet1", ttl=0)
                
                # If email exists, update their row
                if email in df['Email'].values:
                    # Find the index of the user
                    idx = df[df['Email'] == email].index[0]
                    
                    # Update status and timestamp
                    df.at[idx, 'Session'] = "Online"
                    df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Push changes to Google Sheets
                    conn.update(worksheet="Sheet1", data=df)
                    
                    # Mark as checked for this session
                    st.session_state.status_checked = True
            except Exception as e:
                # Silent fail so the user app doesn't crash if API is busy
                print(f"Heartbeat Error: {e}")

    # 3. PAGE CONTENT
    st.title(f"📟 Welcome, {name}")
    st.success("Authorized Access Granted. System Online.")
    
    st.divider()
    st.info("Live Feed: No new intelligence alerts.")

    # 4. LOGOUT LOGIC
    if st.button("🔒 Complete Logout"):
        if email:
            try:
                # Set them to OFFLINE before clearing session
                df = conn.read(worksheet="Sheet1", ttl=0)
                if email in df['Email'].values:
                    # Find index and update
                    idx = df[df['Email'] == email].index[0]
                    df.at[idx, 'Session'] = "Offline"
                    conn.update(worksheet="Sheet1", data=df)
            except Exception as e:
                st.error(f"Logout Error: {e}")

        # Clear everything and restart
        st.query_params.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()