import streamlit as st
from datetime import datetime, timedelta

def show_dashboard(conn):
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title("👥 Admin Control")
    with col2:
        if st.button("🔒 Logout"):
            # Clear everything to ensure a clean exit
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # ... rest of your admin logic (Sync, Approve, etc.) ...
    st.write("Admin Dashboard Active.")