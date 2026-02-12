import streamlit as st
import pandas as pd
import random
from datetime import datetime

# --- 1. HEARTBEAT (Keeps User Online) ---
def run_heartbeat(conn):
    # SAFETY CHECK: If Admin is previewing, DO NOT update database
    if st.session_state.get("admin_verified"):
        return

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

# --- 2. TAB FUNCTIONS ---
def tab_overview():
    # Show "Admin Preview" if admin is watching
    user_name = st.session_state.get('user_name', 'Agent')
    if st.session_state.get("admin_verified"):
        user_name = "Admin (Preview Mode)"
        
    st.header(f"👋 Welcome, {user_name}")
    st.info("System Status: 🟢 ONLINE")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks", "3")
    c2.metric("Efficiency", "94%")
    c3.metric("Next Deadline", "2h 15m")

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
        {"ID": "C-303", "Item": "Router", "Status": "Active"},
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def tab_settings(conn):
    st.header("⚙️ Settings")
    
    # THEME TOGGLE
    st.subheader("🎨 Appearance")
    current_theme = st.session_state.get("theme", "Dark")
    is_dark = True if current_theme == "Dark" else False
    
    if st.toggle("🌙 Dark Mode", value=is_dark):
        st.session_state.theme = "Dark"
    else:
        st.session_state.theme = "Light"
    
    # Only show "Apply" if it actually changed
    if st.button("Apply Theme"):
        st.rerun()

    st.divider()
    
    # Hide "Logout" if Admin is just previewing
    if not st.session_state.get("admin_verified"):
        if st.button("🚪 Log Out", type="primary"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
    else:
        st.info("ℹ️ Logout disabled in Preview Mode.")

# --- 3. MASTER INTERFACE ---
def show_user_interface(conn):
    run_heartbeat(conn)
    
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "🔮 Predictions", "📦 Inventory", "⚙️ Settings"])
    
    with t1: tab_overview()
    with t2: tab_predictions()
    with t3: tab_inventory()
    with t4: tab_settings(conn)