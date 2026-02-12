import streamlit as st

def show_home():
    st.title(f"📟 Welcome, {st.session_state.user_name}")
    st.success("Authorized Access Granted.")
    if st.button("Logout"):
        st.session_state.user_verified = False
        st.rerun()