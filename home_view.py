import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime
import item_monitor
import predictor

# --- 1. HEARTBEAT & EXPIRY ---
def run_heartbeat(conn):
    if st.session_state.get("admin_verified"): return "Active"

    email_param = st.query_params.get("u")
    if not email_param: return "No Email"

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # SMART MATCH: Clean both sides to ensure they match
        clean_param = email_param.strip().lower()
        # Create a temporary column for matching so we don't break original data
        match_series = df['Email'].astype(str).str.strip().str.lower()
        
        if clean_param in match_series.values:
            # Find the true index in the original dataframe
            idx = match_series[match_series == clean_param].index[0]
            user_row = df.iloc[idx]
            
            # Check Expiry
            expiry_str = str(user_row.get('Expiry', ''))
            if expiry_str and expiry_str.strip() != "":
                try:
                    expiry_date = pd.to_datetime(expiry_str)
                    if datetime.now() > expiry_date:
                        return "Expired"
                except: pass

            # Update Online Status
            if "status_checked" not in st.session_state:
                df.at[idx, 'Session'] = "Online"
                df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.update(worksheet="Sheet1", data=df)
                st.session_state.status_checked = True
            
            return "Active"
            
    except Exception as e:
        print(f"Heartbeat Error: {e}")
        return "Active"
    
    return "Active"

# --- 2. TABS ---

def tab_overview(conn, email):
    user = st.session_state.get('user_name', 'Agent')
    if st.session_state.get("admin_verified"): user = "Admin (Preview)"
    
    st.header(f"👋 Welcome, {user}")
    
    days_left = "∞"
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        # Smart Match for Display
        clean_email = email.strip().lower()
        match = df[df['Email'].astype(str).str.strip().str.lower() == clean_email]
        if not match.empty:
            expiry_str = str(match.iloc[0].get('Expiry', ''))
            if expiry_str and expiry_str != "":
                exp_date = pd.to_datetime(expiry_str)
                delta = exp_date - datetime.now()
                days_left = f"{delta.days} Days"
    except: pass

    st.info("System Status: 🟢 ONLINE")
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscription", days_left)
    c2.metric("Efficiency", "98%")
    c3.metric("Tasks", "5")

def tab_settings(conn):
    st.header("⚙️ Settings")
    
    # --- 🎯 STRATEGY TUNER ---
    with st.expander("🎯 Intelligence Strategy Tuner", expanded=False):
        predictor.show_strategy_tuner()
    
    st.divider()
    
    # --- 🔌 STEAMDT API SECTION ---
    with st.container(border=True):
        st.subheader("🔌 API Configuration")
        
        try:
            df = conn.read(worksheet="Sheet1", ttl=0)
            df = df.fillna("")
            
            # Get Email from URL
            email_param = st.query_params.get("u")
            
            # --- DEBUG INFO (Only shows if something is wrong) ---
            if not email_param:
                st.error("Error: No user email detected in URL.")
                st.stop()
                
            # SMART MATCH LOGIC
            clean_param = email_param.strip().lower()
            match_series = df['Email'].astype(str).str.strip().str.lower()
            
            # Check if user exists
            if clean_param in match_series.values:
                # Get the row index
                idx = match_series[match_series == clean_param].index[0]
                user_row = df.iloc[idx]
                
                # Check current key
                current_key = ""
                if "SteamDT API" in df.columns:
                    val = user_row.get("SteamDT API", "")
                    if pd.notna(val) and str(val) != "nan":
                        current_key = str(val)
                else:
                    # Auto-create column if missing
                    df["SteamDT API"] = ""
                    conn.update(worksheet="Sheet1", data=df)
                    st.rerun()

                # Status
                if current_key: st.caption("Status: 🟢 Key Saved")
                else: st.caption("Status: 🔴 No Key Found")

                # Input
                new_key = st.text_input("SteamDT API Key", value=current_key, type="password")
                
                if st.button("💾 Save API Key"):
                    # Update EXACT row index
                    df.at[idx, "SteamDT API"] = new_key
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("Key Saved Successfully!")
                    st.rerun()
            else:
                st.error(f"User '{email_param}' not found in database.")
                st.write("Debug: available emails ->", df['Email'].tolist())

        except Exception as e:
            st.error(f"Settings Error: {e}")

    st.divider()

    with st.expander("🔐 Security Profile"):
        st.text_input("Email", value=st.query_params.get("u"), disabled=True)
        st.text_input("New Password", type="password")
        if st.button("Update Password"):
            st.toast("Request sent to Admin.")

    st.divider()
    
    if not st.session_state.get("admin_verified"):
        if st.button("🚪 Log Out", type="primary"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

# --- 3. MASTER INTERFACE ---
def show_user_interface(conn):
    # Initialize prediction weights
    if "w_abs" not in st.session_state:
        st.session_state.w_abs = 0.4
    if "w_mom" not in st.session_state:
        st.session_state.w_mom = 0.3
    if "w_div" not in st.session_state:
        st.session_state.w_div = 0.3
    
    status = run_heartbeat(conn)
    if status == "Expired":
        st.error("⛔ Subscription Expired.")
        if st.button("Login"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
        return

    email = st.query_params.get("u")
    t1, t2, t3, t4, t5 = st.tabs(["🏠 Overview", "📊 Item Monitor", "📈 Permanent", "📅 Daily", "⚙️ Settings"])
    with t1: tab_overview(conn, email)
    with t2: item_monitor.show_item_monitor(conn)
    with t3: predictor.show_predictor_view(conn, "Permanent")
    with t4: predictor.show_predictor_view(conn, "Daily")
    with t5: tab_settings(conn)
