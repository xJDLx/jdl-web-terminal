import streamlit as st
import pandas as pd
from datetime import datetime

def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        # 1. FETCH & CLEAN
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # --- 🚨 NEW: PENDING REQUESTS ALERT SYSTEM ---
        pending_users = df[df['Status'] == 'Pending']
        
        if not pending_users.empty:
            with st.container(border=True):
                st.error(f"🔔 ACTION REQUIRED: {len(pending_users)} New User Request(s)")
                
                # Loop through each pending user to show quick actions
                for index, row in pending_users.iterrows():
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                    c1.markdown(f"**{row['Name']}**")
                    c2.markdown(f"`{row['Email']}`")
                    
                    # Approve Button
                    if c3.button("✅ Approve", key=f"app_{index}", use_container_width=True):
                        df.at[index, 'Status'] = "Approved"
                        df.at[index, 'Session'] = "Offline"
                        # Set default expiry (e.g., 30 days from now)
                        df.at[index, 'Expiry'] = (datetime.now() + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
                        conn.update(worksheet="Sheet1", data=df)
                        st.success(f"Approved {row['Name']}!")
                        st.rerun()
                        
                    # Deny Button
                    if c4.button("❌ Deny", key=f"deny_{index}", use_container_width=True):
                        df.at[index, 'Status'] = "Denied"
                        conn.update(worksheet="Sheet1", data=df)
                        st.warning(f"Denied {row['Name']}.")
                        st.rerun()

        # 2. STANDARD METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending", len(pending_users))
        c3.metric("Total Users", len(df))
        c4.metric("System Status", "🟢 Nominal")
        
        st.divider()
        
        # 3. QUICK OPS & SEARCH
        col_actions, col_search = st.columns([0.4, 0.6])
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                # Clean dates for saving
                save_df = df.copy()
                save_df['Expiry'] = save_df['Expiry'].astype(str).replace('NaT', '')
                save_df['Last Login'] = save_df['Last Login'].astype(str).replace('NaT', '')
                conn.update(worksheet="Sheet1", data=save_df)
                st.rerun()

        with col_search:
            st.subheader("🔍 Database Search")
            search = st.text_input("Filter", placeholder="User, Email...", label_visibility="collapsed")

        # 4. FILTER LOGIC
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # 5. DATA EDITOR (The Big Table)
        st.markdown("### 🗂️ Master Database")
        
        # Safe Date Conversion for Display
        if 'Expiry' in df_display.columns:
            df_display['Expiry'] = pd.to_datetime(df_display['Expiry'], errors='coerce')
        if 'Last Login' in df_display.columns:
            df_display['Last Login'] = pd.to_datetime(df_display['Last Login'], errors='coerce')

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=600,
            num_rows="dynamic",
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"]),
                "Password": None, # Hidden
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm", disabled=True),
                "Expiry": st.column_config.DateColumn("Expiry", format="YYYY-MM-DD")
            }
        )
        
        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            # Clean for Google Sheets
            final_df = edited_df.copy()
            final_df['Expiry'] = final_df['Expiry'].astype(str).replace('NaT', '')
            final_df['Last Login'] = final_df['Last Login'].astype(str).replace('NaT', '')
            
            conn.update(worksheet="Sheet1", data=final_df)
            st.success("✅ Database Saved!")

    except Exception as e:
        st.error(f"System Error: {e}")