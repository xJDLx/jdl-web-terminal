import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        # 1. FETCH & CLEAN
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # Convert Date Columns for Editing
        if 'Expiry' in df.columns:
            df['Expiry'] = pd.to_datetime(df['Expiry'], errors='coerce')
        if 'Last Login' in df.columns:
            df['Last Login'] = pd.to_datetime(df['Last Login'], errors='coerce')

        # 2. METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))
        # Calculate Expired Users
        expired_count = 0
        now = datetime.now()
        if 'Expiry' in df.columns:
            # Count rows where Expiry is in the past
            expired_count = len(df[df['Expiry'] < now])
        
        c3.metric("Expired Accounts", expired_count)
        c4.metric("Total Members", len(df))
        
        st.divider()
        
        # 3. ACTIONS
        col_actions, col_search = st.columns([0.4, 0.6])
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Force Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                # Convert dates to string before saving
                save_df = df.copy()
                save_df['Expiry'] = save_df['Expiry'].astype(str).replace('NaT', '')
                save_df['Last Login'] = save_df['Last Login'].astype(str).replace('NaT', '')
                conn.update(worksheet="Sheet1", data=save_df)
                st.rerun()

        with col_search:
            st.subheader("🔍 Database Search")
            search = st.text_input("Filter", placeholder="User, Email, Status...", label_visibility="collapsed")

        # 4. FILTER
        if search:
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
                "Password": None, # Hide Password
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm", disabled=True),
                # THE NEW TIMER CONTROL
                "Expiry": st.column_config.DateColumn("Expiry", min_value=datetime(2023, 1, 1), format="YYYY-MM-DD")
            }
        )
        
        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            # Clean up dates for Google Sheets (Prevent System Error)
            final_df = edited_df.copy()
            final_df['Expiry'] = final_df['Expiry'].astype(str).replace('NaT', '')
            final_df['Last Login'] = final_df['Last Login'].astype(str).replace('NaT', '')
            
            conn.update(worksheet="Sheet1", data=final_df)
            st.success("✅ Database updated successfully!")

    except Exception as e:
        st.error(f"System Error: {e}")