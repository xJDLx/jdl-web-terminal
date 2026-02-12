import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. COMMAND CENTER (Metrics + Table) ---
def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        # REMOVED the 'dropna' so you can see ALL rows, even empty ones
        df = df.fillna("") 
        
        # METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Members", len(df))
        c4.metric("System Health", "100%")
        
        st.divider()
        
        # ACTIONS
        st.subheader("⚡ Quick Actions")
        b1, b2 = st.columns(2)
        if b1.button("🔄 Force Sync", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if b2.button("⚠️ Reset All Offline", use_container_width=True):
            df['Session'] = "Offline"
            conn.update(worksheet="Sheet1", data=df)
            st.rerun()
            
        st.divider()
        
        # THE TABLE (Embedded here for convenience)
        st.subheader("📋 Member Overview")
        st.dataframe(df, use_container_width=True, height=300)

    except Exception as e:
        st.error(f"Error: {e}")

# --- 2. FULL DATABASE VIEW (The "Big" Table) ---
def show_database_view(conn):
    st.title("🗂️ Master Database")
    
    # Search Bar
    search = st.text_input("🔍 Search Members", placeholder="Type name, email, or status...")
    
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df = df[mask]

        # Editable Table
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            height=700, # Much taller so you can see everyone
            num_rows="dynamic", # Allows you to ADD rows
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"]),
                "Password": st.column_config.TextColumn("Password", type="password")
            }
        )
        
        if st.button("💾 Save Database Changes", type="primary"):
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("Database Updated!")
            
    except Exception as e:
        st.error(f"Database Error: {e}")