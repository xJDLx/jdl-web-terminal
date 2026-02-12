import streamlit as st
from datetime import datetime

def show_dashboard(conn):
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title("👥 Admin Command")
    with col2:
        if st.button("🔒 Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # 1. FORCE SYNC
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear()
        st.rerun()

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # 2. CALCULATE METRICS
        # Count strictly "Online" users
        online_count = len(df[df['Session'] == 'Online'])
        pending_count = len(df[df['Status'] == 'Pending'])
        
        # Display the Dashboard metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("🟢 Active Users", online_count)
        m2.metric("🟠 Pending Requests", pending_count)
        m3.metric("👥 Total Members", len(df))

        # 3. SESSION CLEANUP TOOL (Fixes the "Stuck Online" issue)
        with st.expander("🛠️ Maintenance Tools"):
            st.warning("Use this if users appear 'Online' but are actually gone.")
            if st.button("⚠️ Force Reset All to 'Offline'"):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.success("All user sessions have been reset to Offline.")
                st.rerun()

        # 4. DATA TABLE
        st.subheader("Live User Database")
        # Highlight "Online" users in the table for visibility
        st.dataframe(
            df.style.apply(lambda x: ['background-color: #d4edda' if x.Session == 'Online' else '' for i in x], axis=1),
            use_container_width=True
        )

        # 5. APPROVAL LOGIC
        # (Keep your existing approval logic here...)

    except Exception as e:
        st.error(f"Sync Error: {e}")