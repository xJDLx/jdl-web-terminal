import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        # 1. FETCH & PREPARE DATA
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("") # Show all rows, even if empty
        
        # 2. METRICS (Top Row)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Members", len(df))
        c4.metric("System Health", "100%")
        
        st.divider()
        
        # 3. ACTIONS & SEARCH (Middle Row)
        col_actions, col_search = st.columns([0.4, 0.6])
        
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Force Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.rerun()

        with col_search:
            st.subheader("🔍 Database Search")
            search = st.text_input("Filter", placeholder="Type name, email, or status...", label_visibility="collapsed")

        # 4. FILTER LOGIC
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # 5. THE MAIN TABLE (Bottom)
        st.markdown("### 🗂️ Master Database")
        
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=600, # Tall enough to see many members
            num_rows="dynamic", # Allows adding new rows
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"]),
                "Password": st.column_config.TextColumn("Password", type="password"),
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm"),
            }
        )
        
        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("✅ Database updated successfully!")

    except Exception as e:
        st.error(f"System Error: {e}")