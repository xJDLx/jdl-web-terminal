import streamlit as st
import pandas as pd
from datetime import datetime
import random # For demo predictions

# --- 1. HEARTBEAT SYSTEM (Keeps User "Online") ---
def run_heartbeat(conn):
    """Updates the database to show the user is active."""
    if "status_checked" not in st.session_state:
        email = st.query_params.get("u")
        if email:
            try:
                df = conn.read(worksheet="Sheet1", ttl=0)
                if email in df['Email'].values:
                    idx = df[df['Email'] == email].index[0]
                    df.at[idx, 'Session'] = "Online"
                    df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.update(worksheet="Sheet1", data=df)
                    st.session_state.status_checked = True
            except:
                pass

# --- 2. PAGE CONTENT FUNCTIONS ---

def tab_overview():
    st.header(f"👋 Welcome, {st.session_state.get('user_name', 'Agent')}")
    st.info("System Status: 🟢 ONLINE")
    
    # Simple Stats Row
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks Pending", "3")
    c2.metric("Next Deadline", "2h 15m")
    c3.metric("Efficiency", "94%")
    
    st.divider()
    st.subheader("📢 Announcements")
    st.warning("Maintenance scheduled for Friday at 03:00 UTC.")

def tab_predictions():
    st.header("🔮 AI Predictions")
    
    # Mock Data for the chart
    st.caption("Projected Resource Usage (Next 24 Hours)")
    chart_data = pd.DataFrame({
        "Hour": range(24),
        "Load": [random.randint(20, 90) for _ in range(24)]
    })
    st.line_chart(chart_data.set_index("Hour"))
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("✅ Prediction: High Traffic expected at 14:00.")
    with c2:
        st.error("⚠️ Risk Alert: Server load may exceed 85%.")

def tab_inventory():
    st.header("📦 Asset Inventory")
    
    # Mock Inventory Data (Replace with real DB read later)
    inventory_data = pd.DataFrame([
        {"Item ID": "A-101", "Name": "Server Blade X1", "Status": "In Use", "Location": "Rack 4"},
        {"Item ID": "A-102", "Name": "Network Switch", "Status": "Available", "Location": "Storage B"},
        {"Item ID": "B-205", "Name": "Cooling Unit", "Status": "Maintenance", "Location": "Roof"},
        {"Item ID": "C-991", "Name": "Backup Drive 4TB", "Status": "Available", "Location": "Safe 1"},
    ])
    
    # Search Bar
    search = st.text_input("🔍 Search Inventory")
    if search:
        inventory_data = inventory_data[inventory_data["Name"].str.contains(search, case=False)]
    
    st.dataframe(inventory_data, use_container_width=True, hide_index=True)

def tab_settings(conn):
    st.header("⚙️ User Settings")
    
    with st.expander("🔐 Security", expanded=True):
        current = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Update Password"):
            st.toast("Password update feature coming soon (requires DB write).")

    with st.expander("🎨 Appearance"):
        st.toggle("Dark Mode", value=True, disabled=True)
        st.caption("Theme managed by Admin.")
        
    st.divider()
    if st.button("🚪 Log Out", type="secondary"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# --- 3. MASTER INTERFACE FUNCTION ---
def show_user_interface(conn):
    # 1. Run the Heartbeat
    run_heartbeat(conn)
    
    # 2. Create the Tabs
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "🔮 Predictions", "📦 Inventory", "⚙️ Settings"])
    
    with t1: tab_overview()
    with t2: tab_predictions()
    with t3: tab_inventory()
    with t4: tab_settings(conn)