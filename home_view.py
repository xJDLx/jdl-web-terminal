import streamlit as st
import database_utils as db # If you created this, otherwise use your connection logic

def show_home(conn):
    name = st.session_state.get("user_name", "Member")
    st.title(f"📟 Welcome, {name}")
    
    if st.button("🔒 Complete Logout"):
        # Set session to Offline in the sheet
        df = conn.read(worksheet="Sheet1", ttl=0)
        email = st.query_params.get("u") # Requires email to be in URL
        if email:
            df.loc[df['Email'] == email, 'Session'] = "Offline"
            conn.update(worksheet="Sheet1", data=df)
            
        st.query_params.clear()
        st.session_state.user_verified = False
        st.rerun()