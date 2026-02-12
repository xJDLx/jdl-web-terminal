import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- VIEW 1: EXECUTIVE DASHBOARD ---
def show_dashboard(conn):
    st.title("📊 Executive Dashboard")
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # Metrics Row
        c1, c2, c3 = st.columns(3)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Users", len(df))
        
        st.divider()
        
        # Actions Area
        st.subheader("⚡ Quick Operations")
        c_left, c_right = st.columns(2)
        with c_left:
            if st.button("🔄 Sync Live Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with c_right:
            if st.button("⚠️ Reset Offline Status", help="Fixes stuck users", use_container_width=True):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.rerun()

    except Exception as e:
        st.error(f"Dashboard Error: {e}")

# --- VIEW 2: MASTER REGISTRY ---
def show_catalog_view(conn):
    st.title("🗂️ Master User Registry")
    
    # Search Bar
    search = st.text_input("🔍 Search Database", placeholder="Type name or email...")
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        if search:
            df = df[df['Name'].str.lower().contains(search.lower())]
        
        # Editable Data Table
        edited_df = st.data_editor(
            df, 
            use_container_width=True, 
            height=600,
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"])
            }
        )
        
        if st.button("💾 Save Changes to Database", type="primary"):
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("Database Updated Successfully!")
            
    except Exception as e:
        st.error(f"Registry Error: {e}")