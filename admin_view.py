import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- HELPER FUNCTIONS ---
def get_time_ago(last_login_str):
    try:
        if not last_login_str or str(last_login_str) == "Never": return "Never"
        last = datetime.strptime(str(last_login_str), "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last
        minutes = int(diff.total_seconds() / 60)
        return "🟢 Online" if minutes < 1 else f"{minutes}m ago"
    except: return "Unknown"

# --- THE UNIFIED VIEW ---
def show_command_center(conn):
    st.title("🛡️ Admin Command Center")
    
    try:
        # 1. FETCH DATA
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(subset=['Email'])
        
        # 2. METRICS ROW (Top of Page)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Active", len(df[df['Session'] == 'Online']))
        c2.metric("🟠 Pending", len(df[df['Status'] == 'Pending']))
        c3.metric("👥 Total Users", len(df))
        c4.metric("📅 New Today", len(df[df['Date'] == datetime.now().strftime("%Y-%m-%d")]))
        
        st.divider()

        # 3. ACTION BAR (Middle)
        col_actions, col_search = st.columns([0.4, 0.6])
        
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Sync Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", help="Fix stuck online users", use_container_width=True):
                df['Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
                st.toast("All sessions reset to Offline.")
                st.rerun()

        with col_search:
            st.subheader("🔍 Filter Registry")
            search = st.text_input("Search", placeholder="Name, Email, or Status...", label_visibility="collapsed")

        # 4. THE REGISTRY TABLE (Bottom)
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.markdown("### 🗂️ Master Database")
        
        # Editable Grid
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=500,
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"], width="small"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"], width="small"),
                "Password": st.column_config.TextColumn("Password", type="password"), # Hide passwords
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm"),
            }
        )

        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            conn.update(worksheet="Sheet1", data=edited_df)
            st.success("✅ Database successfully updated!")

    except Exception as e:
        st.error(f"Command Center Error: {e}")