import streamlit as st

def show_home(conn):
    # Retrieve user info from session state
    name = st.session_state.get("user_name", "Member")
    email = st.query_params.get("u")
    
    st.title(f"📟 Welcome, {name}")
    st.success("Authorized Access Granted.")
    
    st.divider()
    # Your Member Content goes here
    st.info("System Status: Nominal. No active alerts.")

    if st.button("🔒 Complete Logout"):
        # 1. Update Status to Offline in Google Sheets
        if email:
            try:
                df = conn.read(worksheet="Sheet1", ttl=0)
                df.loc[df['Email'] == email, 'Session'] = "Offline"
                conn.update(worksheet="Sheet1", data=df)
            except Exception as e:
                st.error(f"Logout Sync Error: {e}")

        # 2. Clear Session and URL
        st.query_params.clear()
        st.session_state.user_verified = False
        st.rerun()