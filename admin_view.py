import streamlit as st
import pandas as pd
from datetime import datetime

# Helper for "Time Ago"
def get_time_ago(last_login_str):
    try:
        if not last_login_str or str(last_login_str) == "Never":
            return "Never"
        last_active = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last_active
        minutes = int(diff.total_seconds() / 60)
        
        if minutes < 1: return "🟢 Online Now"
        elif minutes < 60: return f"{minutes}m ago"
        elif minutes < 1440: return f"{int(minutes/60)}h ago"
        else: return f"{int(minutes/1440)}d ago"
    except: return "Unknown"

# --- THEME STYLING FUNCTION ---
def style_dataframe(row):
    # Default Color (Dark Gray Text on Black)
    styles = ['background-color: #0e1117; color: #b2b2b2'] * len(row)
    
    # If User is ONLINE -> Bright Green Background, Black Text
    if row['Session'] == 'Online':
        styles = ['background-color: #00ff41; color: #000000; font-weight: bold'] * len(row)
    
    # If User is PENDING -> Yellow Text
    elif row['Status'] == 'Pending':
        styles = ['background-color: #0e1117; color: #ffeb3b'] * len(row)
        
    return styles

def show_dashboard(conn):
    col1, col2 = st.columns([0.8, 0.2])
    with col1: st.title("👥 Admin Command")
    with col2:
        if st.button("🔒 Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear()
        st.rerun()

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Calculate Columns
        if 'Last Login' in df.columns:
            df['Last Active'] = df['Last Login'].apply(get_time_ago)
        else: df['Last Active'] = "Never"

        # Metrics
        online = len(df[df['Session'] == 'Online'])
        pending = len(df[df['Status'] == 'Pending'])
        m1, m2, m3 = st.columns(3)
        m1.metric("Active", online)
        m2.metric("Pending", pending)
        m3.metric("Total", len(df))

        # Maintenance
        with st.expander("🛠️ Maintenance"):
            if st.button("⚠️ Force Offline Reset"):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.success("Reset Complete.")
                st.rerun()

        # --- THE MATCHING TABLE ---
        st.subheader("Live User Database")
        cols = ['Name', 'Email', 'Status', 'Session', 'Last Active', 'Expiry']
        final_cols = [c for c in cols if c in df.columns]
        
        # Apply the dark/hacker theme
        st.dataframe(
            df[final_cols].style.apply(style_dataframe, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Approvals
        st.divider()
        st.subheader("Manage Access")
        pending_list = df[df['Status'] == 'Pending']['Name'].tolist()
        if pending_list:
            target = st.selectbox("Select User", pending_list)
            days = st.number_input("Days:", value=30)
            if st.button("Approve"):
                from datetime import timedelta
                new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                df.loc[df['Name'] == target, 'Status'] = "Approved"
                df.loc[df['Name'] == target, 'Expiry'] = new_expiry
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"{target} Approved.")
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")