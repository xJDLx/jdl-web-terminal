import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime
import item_monitor
import predictor
from sheets_config import read_sheet, update_sheet

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

            # Update Online Status - only once every 5 minutes
            current_time = datetime.now()
            last_update = st.session_state.get('last_status_update')
            
            if not last_update or (current_time - last_update).total_seconds() > 300:
                df.at[idx, 'Session'] = "Online"
                df.at[idx, 'Last Login'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                update_sheet("CSGO_Database", "Sheet1", df)
                st.session_state.last_status_update = current_time
            
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
    
    # API key management is now handled in item_monitor.py
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
