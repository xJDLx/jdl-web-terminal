import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- HELPER FUNCTIONS ---
def get_time_ago(last_login_str):
    try:
        if not last_login_str or str(last_login_str) == "Never":
            return "Never"
        
        last_active = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last_active
        minutes = int(diff.total_seconds() / 60)
        
        if minutes < 1:
            return "🟢 Just Now"
        elif minutes < 60:
            return f"{minutes}m ago"
        elif minutes < 1440:
            hours = int(minutes / 60)
            return f"{hours}h ago"
        else:
            days = int(minutes / 1440)
            return f"{days}d ago"
    except:
        return "Unknown"

# --- MAIN DASHBOARD ---
def show_dashboard(conn):
    # 1. TOP BAR
    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        st.title("🛡️ Command Center")
    with c2: 
        if st.button("🔒 Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # 2. DATA LOADING
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Calculate 'Last Active' column
        if 'Last Login' in df.columns:
            df['Last Active'] = df['Last Login'].apply(get_time_ago)
        else:
            df['Last Active'] = "Never"

        # 3. KPI CARDS
        st.markdown("### System Metrics")
        k1, k2, k3, k4 = st.columns(4)
        
        online = len(df[df['Session'] == 'Online'])
        pending = len(df[df['Status'] == 'Pending'])
        total = len(df)
        
        # Safe check for new users
        today_str = datetime.now().strftime("%Y-%m-%d")
        new_today = len(df[df['Date'] == today_str])

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
                mask = df['Name'].str.lower().contains(search) | df['Email'].str.lower().contains(search)
                df = df[mask]

            # Simplified Table Display (Removed complex styling to prevent syntax errors)
            display_cols = ['Name', 'Status', 'Session', 'Last Active', 'Expiry']
            final_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[final_cols], use_container_width=True, height=400)

        with col_side:
            st.subheader("⚡ Quick Actions")
            with st.container(border=True):
                if st.button("🔄 Sync Live Data", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
                
                if st.button("⚠️ Reset Offline Status", help="Fixes stuck users", use_container_width=True):
                    df['Session'] = "Offline"
                    conn.update(worksheet="Sheet1", data=df)
                    st.toast("System Reset Complete")
                    st.rerun()

            st.subheader("✅ Approvals")
            with st.container(border=True):
                pending_list = df[df['Status'] == 'Pending']['Name'].tolist()
                if pending_list:
                    target = st.selectbox("Select Request", pending_list)
                    days = st.number_input("Access Duration", value=30, min_value=1)
                    
                    c_approve, c_deny = st.columns(2)
                    with c_approve:
                        if st.button("Approve", type="primary", use_container_width=True):
                            new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                            df.loc[df['Name'] == target, 'Status'] = "Approved"
                            df.loc[df['Name'] == target, 'Expiry'] = new_expiry
                            conn.update(worksheet="Sheet1", data=df)
                            st.rerun()
                    with c_deny:
                         if st.button("Deny", use_container_width=True):
                            df.loc[df['Name'] == target, 'Status'] = "Denied"
                            conn.update(worksheet="Sheet1", data=df)
                            st.rerun()
                else:
                    st.info("No pending requests.")

    except Exception as e:
        st.error(f"Connection Error: {e}")