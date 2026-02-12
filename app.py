import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. PAGE SETUP
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 2. HIDE DEFAULT MENU (The "Pro" Touch)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. STATE INITIALIZATION
if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

# 4. REFRESH LOGIC
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

# 5. PROFESSIONAL SIDEBAR NAVIGATION
def main():
    if st.session_state.admin_verified:
        with st.sidebar:
            st.header("JDL Command")
            st.success("Admin Access Active")
            page = st.radio("Navigation", ["Dashboard", "User Management", "System Logs"])
            st.divider()
            if st.button("🔒 Secure Logout", use_container_width=True):
                st.query_params.clear()
                st.session_state.admin_verified = False
                st.rerun()
        
        # Route to views (We can split admin_view later, for now all go to dashboard)
        admin_view.show_dashboard(conn)

    elif st.session_state.user_verified:
        with st.sidebar:
            st.header(f"User: {st.session_state.get('user_name', 'Member')}")
            st.info("Status: Online")
            page = st.radio("Menu", ["Live Feed", "Resources", "Profile"])
            st.divider()
            if st.button("🔒 Logout", use_container_width=True):
                # (Logout logic here - kept brief for display)
                st.query_params.clear()
                st.session_state.user_verified = False
                st.rerun()
        
        home_view.show_home(conn)

    else:
        # Login page stays full screen (No Sidebar)
        gatekeeper.show_login(conn)

if __name__ == "__main__":
    main()