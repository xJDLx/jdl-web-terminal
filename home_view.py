import streamlit as st

def show_home(conn):
    st.title(f"📟 Welcome, {st.session_state.get('user_name')}")
    
    # ... your content ...

    if st.button("🔒 Logout"):
        email = st.query_params.get("u") # Or verify via name lookup if u is missing
        # Safety fallback: if 'u' isn't in URL, try to find by name in session
        if not email and "user_name" in st.session_state:
            # Logic to find email by name could go here, or just rely on manual reset
            pass

        try:
            df = conn.read(worksheet="Sheet1", ttl=0)
            # Mark ONLY this user as offline
            # (Requires you to track email in session state or URL)
            # For now, we rely on the Admin "Force Reset" if this fails
            pass 
        except:
            pass
        
        st.query_params.clear()
        st.session_state.user_verified = False
        st.rerun()