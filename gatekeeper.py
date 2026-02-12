import streamlit as st

def show_login(conn):
    # ... (inside your Member Login tab) ...
    email = st.text_input("Member Email").strip().lower()
    remember = st.checkbox("Stay Logged In")
    
    if st.button("Access Terminal"):
        df = conn.read(worksheet="Sheet1", ttl=0)
        # Verify user logic...
        if str(user['Status']) == "Approved":
            st.session_state.user_verified = True
            if remember:
                # This saves the email in the URL like ?u=email@example.com
                st.query_params["u"] = email 
            st.rerun()