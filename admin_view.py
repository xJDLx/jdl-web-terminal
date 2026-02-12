import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        # 1. FETCH & CLEAN DATA
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # --- THE FIX: Convert 'Last Login' to DateTime objects ---
        if 'Last Login' in df.columns:
            df['Last Login'] = pd.to_datetime(df['Last Login'], errors='coerce')

        # 2. METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        c3.metric("Total Members", len(df))
        c4.metric("System Health", "100%")
        
        st.divider()
        
        # 3. ACTIONS & SEARCH
        col_actions, col_search = st.columns([0.4, 0.6])
        
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Force Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                # Convert back to string for storage if needed, or rely on GSheets handling
                conn.update(worksheet="Sheet1", data=df)
                st.rerun()

        with col_search:
            st.subheader("🔍 Database Search")
            search = st.text_input("Filter", placeholder="Type name, email, or status...", label_visibility="collapsed")

        # 4. FILTER LOGIC
        if search:
            # We convert to string briefly just for searching
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # 5. THE MAIN TABLE
        st.markdown("### 🗂️ Master Database")
        
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=600,
            num_rows="dynamic",
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"]),
                "Password": None, # Hides the password column for security
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm"),
            }
        )
        
        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            # Convert datetime back to string format for Google Sheets compatibility
            if 'Last Login' in edited_df.columns:
                edited_df['Last Login'] = edited_df['Last Login'].astype(str)
                
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("✅ Database updated successfully!")

    except Exception as e:
        st.error(f"System Error: {e}")