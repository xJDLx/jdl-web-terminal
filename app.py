import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="JDL Data Registry",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. PROFESSIONAL STYLING (CSS Injection)
st.markdown("""
    <style>
    /* Remove default top padding */
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    /* Clean up the sidebar */
    [data-testid="stSidebar"] {background-color: #f8f9fa;} 
    /* Dark mode override if you are in dark mode */
    @media (prefers-color-scheme: dark) {
        [data-testid="stSidebar"] {background-color: #111;}
    }
    </style>
""", unsafe_allow_html=True)

# 3. CONNECTION & STATE
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

# 4. REFRESH LOGIC
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

# 5. MAIN APP CONTROLLER
def main():
    if st.session_state.admin_verified:
        # --- CATALOG SIDEBAR ---
        with st.sidebar:
            st.title("🗂️ JDL Registry")
            st.caption("Master User Catalog")
            
            st.markdown("---")
            
            # View Filters (Like the Snowflake App)
            st.subheader("📁 Views")
            view_mode = st.radio(
                "Show:", 
                ["All Users", "Active Sessions", "Pending Requests", "Security Log"],
                index=0,
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            st.subheader("⚙️ System")
            if st.button("🔄 Force Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            
            if st.button("🔒 Secure Logout", use_container_width=True):
                st.query_params.clear()
                st.session_state.admin_verified = False
                st.rerun()

        # Pass the selected view_mode to the admin dashboard
        admin_view.show_catalog(conn, view_mode)

    elif st.session_state.user_verified:
        home_view.show_home(conn)
    else:
        gatekeeper.show_login(conn)

if __name__ == "__main__":
    main()