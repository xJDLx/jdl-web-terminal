import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- VIEW 1: DASHBOARD ---
def show_dashboard(conn):
    st.title("📊 Executive Dashboard")
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Users", len(df))
        
        st.divider()
        
        # Quick Actions
        c_left, c_right = st.columns([0.4, 0.6])
        with c_left:
            st.subheader("⚡ Quick Ops")
            if st.button("🔄 Sync Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if st.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.rerun()

        with c_right:
            st.subheader("📝 Recent Activity")
            st.dataframe(df[['Name', 'Status', 'Last Login']].head(5), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error: {e}")

# --- VIEW 2: REGISTRY ---
def show_catalog_view(conn):
    st.title("🗂️ Master Registry")
    
    # Search
    search = st.text_input("🔍 Search Database")
    
    df = conn.read(worksheet="Sheet1", ttl=0)
    
    if search:
        df = df[df['Name'].str.lower().contains(search.lower())]
    
    # Editable Dataframe
    edited_df = st.data_editor(
        df, 
        use_container_width=True, 
        height=600,
        column_config={
            "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
            "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"])
        }
    )
    
    if st.button("💾 Save Changes", type="primary"):
        conn.update(worksheet="Sheet1", data=edited_df)
        st.success("Database Updated!")