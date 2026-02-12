import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- HELPER FUNCTIONS ---
def get_time_ago(last_login_str):
    try:
        if not last_login_str or str(last_login_str) == "Never": return "Never"
        last_active = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last_active
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1: return "🟢 Just Now"
        elif minutes < 60: return f"{minutes}m ago"
        elif minutes < 1440: return f"{int(minutes/60)}h ago"
        else: return f"{int(minutes/1440)}d ago"
    except: return "Unknown"

def style_status(val):
    color = '#00ff41' if val == 'Online' else '#b2b2b2'
    return f'color: {color}'

# --- MAIN DASHBOARD ---
def show_dashboard(conn):
    # 1. TOP BAR
    c1, c2 = st.columns([0.85, 0.15])
    with c1: st.title("🛡️ Command Center")
    with c2: 
        if st.button("🔒 Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # 2. DATA LOADING
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Calculate 'Last Active' column for display
        if 'Last Login' in df.columns:
            df['Last Active'] = df['Last Login'].apply(get_time_ago)
        else: df['Last Active'] = "Never"

        # 3. KPI CARDS (The "Business" Look)
        st.markdown("### System Metrics")
        k1, k2, k3, k4 = st.columns(4)
        
        online = len(df[df['Session'] == 'Online'])
        pending = len(df[df['Status'] == 'Pending'])
        total = len(df)
        new_today = len(df[df['Date'] == datetime.now().strftime("%Y-%m-%d")])

        k1.metric("🟢 Live Users", online, delta="Active Now")
        k2.metric("🟠 Pending Requests", pending, delta="Action Required", delta_color="inverse")
        k3.metric("👥 Total Members", total)
        k4.metric("📈 New Today", new_today)

        st.divider()

        # 4. SPLIT LAYOUT (Table vs Actions)
        col_main, col_side = st.columns([0.7, 0.3])

        with col_main:
            st.subheader("🌍 User Database")
            
            # Search Bar
            search = st.text_input("🔍 Search Users", placeholder="Type name or email...").lower()
            if search:
                df = df[df['Name'].str.lower().contains(search) | df['Email'].str.lower().contains(search)]

            # Styled Table
            display_cols = ['Name', 'Status', 'Session', 'Last Active', 'Expiry']
            final_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[final_cols].style.map(style_status, subset=['Session']),
                use_container_width=True,
                height=400
            )

        with col_side:
            st.subheader("⚡ Quick Actions")
            with st.container(border=True):
                if