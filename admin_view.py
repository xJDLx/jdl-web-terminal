import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- HELPER: Time Formatting ---
def get_time_ago(last_login_str):
    try:
        if not last_login_str or str(last_login_str) == "Never": return "Never"
        last_active = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last_active
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1: return "🟢 Online Now"
        elif minutes < 60: return f"{minutes}m ago"
        elif minutes < 1440: return f"{int(minutes/60)}h ago"
        else: return f"{int(minutes/1440)}d ago"
    except: return "Unknown"

# --- MAIN CATALOG VIEW ---
def show_catalog(conn, view_mode):
    # 1. FETCH & PREPARE DATA
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Calculate Columns
        if 'Last Login' in df.columns:
            df['Last Active'] = df['Last Login'].apply(get_time_ago)
        else: df['Last Active'] = "Never"

        # 2. FILTER DATA BASED ON SIDEBAR SELECTION
        filtered_df = df.copy()
        if view_mode == "Active Sessions":
            filtered_df = df[df['Session'] == 'Online']
        elif view_mode == "Pending Requests":
            filtered_df = df[df['Status'] == 'Pending']
        elif view_mode == "Security Log":
            # Just an example filter, implies showing everyone for audit
            pass 

    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return

    # 3. TOP METRICS (The "Snowflake" Header)
    st.markdown(f"## 📊 {view_mode}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", len(df))
    m2.metric("Online Now", len(df[df['Session'] == 'Online']))
    m3.metric("Pending Approval", len(df[df['Status'] == 'Pending']))
    m4.metric("System Status", "Healthy")
    
    st.divider()

    # 4. MASTER-DETAIL LAYOUT
    # We use a container for the table and an expander or columns for details
    
    col_table, col_inspector = st.columns([0.65, 0.35])
    
    with col_table:
        st.subheader("Directory")
        
        # Search Bar
        search = st.text_input("🔍 Search Catalog", placeholder="Filter by name, email...")
        if search:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        # THE MAIN TABLE
        # specific columns for clean view
        display_cols = ['Name', 'Email', 'Status', 'Session', 'Last Active']
        final_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[final_cols],
            use_container_width=True,
            height=500,
            hide_index=True
        )

    with col_inspector:
        st.subheader("🕵️ Inspector")
        with st.container(border=True):
            # Select User to Inspect
            # (We use a selectbox because standard dataframes don't support click-events easily yet)
            user_list = filtered_df['Name'].tolist()
            if user_list:
                selected_user = st.selectbox("Select User to Manage", user_list)
                
                # Get User Data
                user_data = df[df['Name'] == selected_user].iloc[0]
                
                # PROFILE CARD
                st.markdown(f"### 👤 {user_data['Name']}")
                st.caption(f"ID: {user_data['Email']}")
                
                # STATUS BADGES
                s1, s2 = st.columns(2)
                s1.info(f"Status: {user_data['Status']}")
                s2.success(f"Session: {user_data.get('Session', 'Offline')}")
                
                st.markdown("---")
                st.write("**Access Controls**")
                
                # APPROVAL WORKFLOW
                if user_data['Status'] == 'Pending':
                    days = st.number_input("Grant Access (Days)", value=30, min_value=1)
                    if st.button("✅ Approve Request", type="primary", use_container_width=True):
                        new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                        df.loc[df['Name'] == selected_user, 'Status'] = "Approved"
                        df.loc[df['Name'] == selected_user, 'Expiry'] = new_expiry
                        conn.update(worksheet="Sheet1", data=df)
                        st.toast(f"{selected_user} Approved!")
                        st.rerun()
                    
                    if st.button("🚫 Deny Access", use_container_width=True):
                        df.loc[df['Name'] == selected_user, 'Status'] = "Denied"
                        conn.update(worksheet="Sheet1", data=df)
                        st.rerun()

                # SESSION MANAGEMENT
                if user_data.get('Session') == 'Online':
                    if st.button("⚠️ Force Logout (Kill Session)", use_container_width=True):
                        df.loc[df['Name'] == selected_user, 'Session'] = "Offline"
                        conn.update(worksheet="Sheet1", data=df)
                        st.toast(f"Session killed for {selected_user}")
                        st.rerun()

                # METADATA
                with st.expander("View Raw Metadata"):
                    st.json(user_data.to_dict())
            else:
                st.info("No users match the current filter.")