import streamlit as st
import pandas as pd
from datetime import datetime

# Helper to calculate "Time Ago"
def get_time_ago(last_login_str):
    try:
        if not last_login_str or last_login_str == "Never":
            return "Never"
        
        # Convert string to datetime object
        last_active = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        
        # Calculate difference
        diff = now - last_active
        minutes = int(diff.total_seconds() / 60)
        
        # Return friendly string
        if minutes < 1:
            return "🟢 Online Now"
        elif minutes < 60:
            return f"🕒 {minutes} mins ago"
        elif minutes < 1440: # Less than 24 hours
            hours = int(minutes / 60)
            return f"🕒 {hours} hours ago"
        else:
            days = int(minutes / 1440)
            return f"📅 {days} days ago"
    except:
        return "Unknown"

def show_dashboard(conn):
    # Top Bar
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title("👥 Admin Command")
    with col2:
        if st.button("🔒 Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # Force Sync Button
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear()
        st.rerun()

    try:
        # 1. READ DATA
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # 2. ADD "LAST ACTIVE" COLUMN (The Fix)
        # We apply the helper function to every row in the 'Last Login' column
        if 'Last Login' in df.columns:
            df['Last Active'] = df['Last Login'].apply(get_time_ago)
        else:
            df['Last Active'] = "No Data"

        # 3. METRICS
        online_count = len(df[df['Session'] == 'Online'])
        pending_count = len(df[df['Status'] == 'Pending'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Active Sessions", online_count)
        m2.metric("Pending Requests", pending_count)
        m3.metric("Total Members", len(df))

        # 4. MAINTENANCE TOOLS
        with st.expander("🛠️ Maintenance Tools"):
            if st.button("⚠️ Reset All Stuck Sessions"):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.success("All statuses reset to Offline.")
                st.rerun()

        # 5. DISPLAY TABLE
        st.subheader("Live User Database")
        
        # Reorder columns to put "Last Active" next to Status for better visibility
        display_cols = ['Name', 'Email', 'Status', 'Session', 'Last Active', 'Expiry', 'Last Login']
        # Filter to only show columns that actually exist in the dataframe
        final_cols = [c for c in display_cols if c in df.columns]
        
        # Show dataframe with highlighting
        st.dataframe(
            df[final_cols].style.apply(
                lambda x: ['background-color: #d4edda' if x.Session == 'Online' else '' for i in x], 
                axis=1
            ),
            use_container_width=True
        )

        # 6. APPROVAL SECTION
        st.divider()
        st.subheader("Manage Access")
        pending_users = df[df['Status'] == 'Pending']['Name'].tolist()
        
        if pending_users:
            target = st.selectbox("Select User", pending_users)
            days = st.number_input("Grant Days:", min_value=1, value=30)
            if st.button("Approve User"):
                from datetime import timedelta
                new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                df.loc[df['Name'] == target, 'Status'] = "Approved"
                df.loc[df['Name'] == target, 'Expiry'] = new_expiry
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"{target} approved!")
                st.rerun()

    except Exception as e:
        st.error(f"Dashboard Error: {e}")