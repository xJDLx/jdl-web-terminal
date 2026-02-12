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
        if minutes < 1: return "🟢 Online"
        else: return f"{minutes}m ago"
    except: return "Unknown"

# --- VIEW 1: MAIN DASHBOARD ---
def show_dashboard(conn):
    st.title("📊 Executive Dashboard")
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # 1. METRIC CARDS
        c1, c2, c3 = st.columns(3)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Users", len(df))
        
        st.markdown("---")

        # 2. TABBED INTERFACE (Clickable Tabs)
        tab1, tab2 = st.tabs(["⚡ Live Activity", "✅ Approvals"])
        
        with tab1:
            st.subheader("Real-time Feed")
            if st.button("🔄 Refresh Feed"):
                st.cache_data.clear()
                st.rerun()
                
            # Show only online users here
            online_df = df[df['Session'] == 'Online']
            if not online_df.empty:
                st.dataframe(online_df[['Name', 'Email', 'Last Login']], use_container_width=True)
            else:
                st.info("No active users right now.")

        with tab2:
            st.subheader("Pending Requests")
            pending = df[df['Status'] == 'Pending']
            
            if not pending.empty:
                # 3. DROPDOWN MENU (Expander)
                # Each user gets their own clickable dropdown
                for index, row in pending.iterrows():
                    with st.expander(f"Request: {row['Name']} ({row['Email']})"):
                        c_days, c_btn = st.columns([0.7, 0.3])
                        days = c_days.number_input(f"Days for {row['Name']}", value=30, key=row['Email'])
                        if c_btn.button(f"Approve {row['Name']}", key=f"btn_{row['Email']}"):
                            # Approval Logic
                            new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                            df.loc[df['Email'] == row['Email'], 'Status'] = "Approved"
                            df.loc[df['Email'] == row['Email'], 'Expiry'] = new_expiry
                            conn.update(worksheet="Sheet1", data=df)
                            st.rerun()
            else:
                st.success("All caught up! No pending requests.")

    except Exception as e:
        st.error(f"Error: {e}")

# --- VIEW 2: FULL REGISTRY (The "User Registry" Tab) ---
def show_catalog_view(conn):
    st.title("🗂️ Master Registry")
    
    # Simple search bar
    search = st.text_input("🔍 Search Database")
    
    df = conn.read(worksheet="Sheet1", ttl=0)
    if search:
        df = df[df['Name'].str.lower().contains(search.lower())]
        
    st.dataframe(df, use_container_width=True, height=600)