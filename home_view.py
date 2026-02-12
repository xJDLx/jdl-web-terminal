import streamlit as st

def show_home():
    st.title("📟 Member Terminal")
    # ... content ...
    
    if st.button("🔒 Complete Logout"):
        st.query_params.clear() # Deletes the saved session from URL
        st.session_state.user_verified = False
        st.rerun()