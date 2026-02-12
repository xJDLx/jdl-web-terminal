import streamlit as st
import pandas as pd
import random
from datetime import datetime

# --- 1. HEARTBEAT & EXPIRY CHECK ---
def run_heartbeat(conn):
    # Admin Override
    if st.session_state.get("admin_verified"): return "Active"

    email = st.query_params.get("u")
    if not email: return "No Email"

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        if email in df['Email'].values:
            user_row = df[df['Email'] == email].iloc[0]
            
            # CHECK EXPIRY
            expiry_str = str(user_row.get('Expiry', ''))
            if expiry_str and expiry_str.strip() != "":
                try:
                    expiry_date = pd.to_datetime(expiry_str)
                    if datetime.now() > expiry_date:
                        return "Expired" # LOCK THE USER OUT
                except:
                    pass # If date format is wrong, assume active for now (safer)

            # Update Online Status if not expired
            if "status_checked" not in st.session_state:
                idx = df[df['Email'] == email].index[0]
                df.at[idx, 'Session'] = "Online"
                df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.update(worksheet="Sheet1", data=df)
                st.session_state.status_checked = True
            
            return "Active"
            
    except Exception as e:
        print(f"Heartbeat Error: {e}")
        return "Active" # Fail open to prevent bugs blocking users
    
    return "Active"

# --- 2. TABS ---
def tab_overview(conn, email):
    user = st.session_state.get('user_name', 'Agent')
    if st.session_state.get("admin_verified"): user = "Admin (Preview)"
    
    st.header(f"👋 Welcome, {user}")
    
    # CALCULATE DAYS REMAINING
    days_left = "∞"
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        user_row = df[df['Email'] == email].iloc[0]
        expiry_str = str(user_row.get('Expiry', ''))
        if expiry_str and expiry_str != "nan" and expiry_str != "":
            exp_date = pd.to_datetime(expiry_str)
            delta = exp_date - datetime.now()
            days_left = f"{delta.days} Days"
    except: pass

    st.info("System Status: 🟢 ONLINE")
    
    # METRICS ROW
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscription", days_left) # SHOWS TIMER
    c2.metric("Efficiency", "94%")
    c3.metric("Tasks", "3")

def tab_predictions():
    st.header("🔮 AI Predictions")
    chart_data = pd.DataFrame({
        "Hour": range(24),
        "Load": [random.randint(20, 90) for _ in range(24)]
    })
    st.line_chart(chart_data.set_index("Hour"))
    st.success("✅ Prediction: Optimal performance expected.")

def tab_inventory():
    st.header("📦 Inventory")
    data = [
        {"ID": "A-101", "Item": "Server Blade", "Status": "Active"},
        {"ID": "B-202", "Item": "Switch", "Status": "Maintenance"},
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def tab_settings(conn):
    st.header("⚙️ Settings")
    
    # API SECTION
    with st.expander("🔌 SteamDT API Integration", expanded=False):
        st.caption("Manage your private SteamDT keys.")
        try:
            df = conn.read(worksheet="Sheet1", ttl=0)
            email = st.query_params.get("u")
            if "SteamDT API" not in df.columns: df["SteamDT API"] = ""
            
            current_key = ""
            if email in df['Email'].values:
                user_row = df[df['Email'] == email].iloc[0]
                if pd.notna(user_row["SteamDT API"]):
                    current_key = str(user_row["SteamDT API"])
            
            new_key = st.text_input("API Key", value=current_key, type="password")
            if st.button("💾 Save API Key"):
                if email in df['Email'].values:
                    idx = df[df['Email'] == email].index[0]
                    df.at[idx, "SteamDT API"] = new_key
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("Updated!")
                    st.rerun()
        except: st.error("Error loading settings.")

    st.divider()
    
    if not st.session_state.get("admin_verified"):
        if st.button("🚪 Log Out", type="primary"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

# --- 3. MASTER INTERFACE ---
def show_user_interface(conn):
    # CHECK EXPIRY STATUS FIRST
    status = run_heartbeat(conn)
    
    if status == "Expired":
        st.error("⛔ ACCESS DENIED: Your subscription has expired.")
        st.warning("Please contact the Administrator to renew your access.")
        if st.button("Return to Login"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
        return # STOP HERE. Do not show tabs.

    # Show Interface if Active
    email = st.query_params.get("u")
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "🔮 Predictions", "📦 Inventory", "⚙️ Settings"])
    with t1: tab_overview(conn, email)
    with t2: tab_predictions()
    with t3: tab_inventory()
    with t4: tab_settings(conn)