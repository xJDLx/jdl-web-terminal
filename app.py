import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. PAGE CONFIG
st.set_page_config(
    page_title="JDL System", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS STYLING
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    
    /* Professional Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #0e1117;
        padding-bottom: 0px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0e1117;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #b2b2b2;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e1e1e;
        border-bottom: 2px solid #00ff41;
        color: #00ff41;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# 3. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

# 4. REFRESH LOGIC
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

def main():
    # --- LOGGED OUT ---
    if not st.session_state.admin_verified and not st.session_state.user_verified:
        gatekeeper.show_login(conn)
        return

    # --- ADMIN VIEW ---
    if st.session_state.admin_verified:
        t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "🗂️ User Registry", "⚙️ System Logs", "🔒 Logout"])
        
        with t1: admin_view.show_dashboard(conn)
        with t2: admin_view.show_catalog_view(conn)
        with t3: 
            st.title("📟 System Event Logs")
            st.info("System Status: Nominal.")
        with t4:
            if st.button("Confirm Logout"):
                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    # --- USER VIEW (The New Interface) ---
    elif st.session_state.user_verified:
        # Call the new 4-page function here
        home_view.show_user_interface(conn)

if __name__ == "__main__":
    main()