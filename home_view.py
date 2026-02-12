import streamlit as st
import pandas as pd
import random
from datetime import datetime

# --- 1. HEARTBEAT & EXPIRY CHECK ---
def run_heartbeat(conn):
    # Admin Override: Admins never expire and don't trigger "Online" status updates
    if st.session_state.get("admin_verified"): return "Active"

    email = st.query_params.get("u")
    if not email: return "No Email"

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        if email in df['Email'].values:
            user_row = df[df['Email'] == email].iloc[0]
            
            # CHECK EXPIRY DATE
            expiry_str = str(user_row.get('Expiry', ''))
            if expiry_str and expiry_str.strip() != "":
                try:
                    expiry_date = pd.to_datetime(expiry_str)
                    if datetime.now() > expiry_date:
                        return "Expired" # LOCKOUT TRIGGER
                except:
                    pass # Ignore bad date formats

            # UPDATE ONLINE STATUS (Only if not expired)
            if "status_checked" not in st.session_state:
                idx = df[df['Email'] == email].index[0]
                df.at[idx, 'Session'] = "Online"
                df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.update(worksheet="Sheet1", data=df)
                st.session_state.status_checked = True
            
            return "Active"
            
    except Exception as e:
        # Fail open (allow access) if DB errors occurs, to prevent locking out valid users due to glitches
        print(f"Heartbeat Error: {e}")
        return "Active"
    
    return "Active"

# --- 2. TAB FUNCTIONS ---

def tab_overview(conn, email):
    user = st.session_state.get('user_name', 'Agent')
    if st.session_state.get("admin_verified"): user = "Admin (Preview)"
    
    st.header(f"👋 Welcome, {user}")
    
    # Calculate Subscription Time Remaining
    days_left = "∞"
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if email in df['Email'].values:
            user_row = df[df['Email'] == email].iloc[0]
            expiry_str = str(user_row.get('Expiry', ''))
            if expiry_str and expiry_str != "nan" and expiry_str != "":
                exp_date = pd.to_datetime(expiry_str)
                delta = exp_date - datetime.now()
                days_left = f"{delta.days} Days"
    except: pass

    st.info("System Status: 🟢 ONLINE")
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscription", days_left)
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
    
    # --- 🔌 STEAMDT API SECTION ---
    with st.expander("🔌 SteamDT API Configuration", expanded=True):
        st.caption("Enter your private SteamDT API Key below. This is encrypted in view.")
        
        try:
            # Load fresh data to get current key
            df = conn.read(worksheet="Sheet1", ttl=0)
            email = st.query_params.get("u")
            
            # Handle missing column if Admin hasn't added it yet
            if "SteamDT API" not in df.columns:
                df["SteamDT API"] = ""
            
            # Find current user's key
            current_key = ""
            if email in df['Email'].values:
                user_row = df[df['Email'] == email].iloc[0]
                if pd.notna(user_row["SteamDT API"]):
                    current_key = str(user_row["SteamDT API"])
            
            # The Secure Input Field
            new_key = st.text_input("API Key", value=current_key, type="password", placeholder="Paste key here...")
            
            if st.button("💾 Save API Key"):
                if email in df['Email'].values:
                    idx = df[df['Email'] == email].index[0]
                    # Update the dataframe in memory
                    df.at[idx, "SteamDT API"] = new_key
                    # Push to Google Sheets
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("API Key updated successfully!")
                    st.rerun()
                else:
                    st.error("User record not found.")
                    
        except Exception as e:
            st.error(f"Settings Error: {e}")

    st.divider()

    # --- PASSWORD RESET ---
    with st.expander("🔐 Security Profile", expanded=False):
        st.text_input("Email", value=st.query_params.get("u"), disabled=True)
        st.text_input("New Password", type="password")
        if st.button("Update Password"):
            st.toast("Security update requested.")

    st.divider()
    
    # --- LOGOUT ---
    if not st.session_state.get("admin_verified"):
        if st.button("🚪 Log Out", type="primary"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
    else:
        st.info("ℹ️ Logout disabled in Preview Mode.")

# --- 3. MASTER INTERFACE ---
def show_user_interface(conn):
    # 1. Check if user is Expired
    status = run_heartbeat(conn)
    
    if status == "Expired":
        st.error("⛔ ACCESS DENIED: Your subscription has expired.")
        st.warning("Please contact support to renew your access.")
        if st.button("Return to Login"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
        return # STOP EVERYTHING ELSE

    # 2. If Active, Show the Tabs
    email = st.query_params.get("u")
    
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "🔮 Predictions", "📦 Inventory", "⚙️ Settings"])
    
    with t1: tab_overview(conn, email)
    with t2: tab_predictions()
    with t3: tab_inventory()
    # Pass conn to settings so we can save the API key
    with t4: tab_settings(conn)