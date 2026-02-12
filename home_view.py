import streamlit as st

def show_home():
    # Wrap logic inside the function so it only runs AFTER app.py is ready
    name = st.session_state.get("user_name", "Authorized Member")
    
    st.title(f"📟 Terminal: Welcome, {name}")
    st.success("Connection Secure. System is Online.")
    
    st.divider()
    # Member Content Here
    st.info("No new intelligence alerts for your sector.")
    
    if st.button("🔒 Logout"):
        st.query_params.clear()
        st.session_state.user_verified = False
        st.rerun()