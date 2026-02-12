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

# 2. CSS STYLING (Dark Mode)
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {background-color: #0e1117;}
    [data-testid="stHeader"] {background-color: #0e1117;}
    [data-testid="stSidebar"] {background-color: #262730;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 2px; background-color: #0e1117; padding-bottom: 0px;}
    .stTabs [data-baseweb="tab"] {height: 50px; background-color: #0e1117; color: #b2b2b2; border-radius: 4px 4px 0px 0px;}
    .stTabs [aria-selected="true"] {background-color: #1e1e1e; border-bottom: 2px solid #00ff41; color: #00ff41;}
    </style>
""", unsafe_allow_html=True)

# 3. CONNECTION & STATE
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

def main():
    if not st.session_state.admin_verified and not st.session_state.user_verified:
        gatekeeper.show_login(conn)
        return

    # --- ADMIN VIEW ---
    if st.session_state.admin_verified:
        # MERGED TABS: Dashboard & Registry are now one "Command Center"
        t1, t2, t3, t4 = st.tabs(["🛡️ Command Center", "👁️ User View", "⚙️ Logs", "🔒 Logout"])
        
        with t1:
            admin_view.show_command_center(conn) # <--- The new unified function
            
        with t2:
            st.warning("⚠️ Admin Preview Mode Active")
            home_view.show_user_interface(conn)
            
        with t3: st.info("System Status: Nominal.")
        
        with t4:
            if st.button("Confirm Logout"):
                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    # --- USER VIEW ---
    elif st.session_state.user_verified:
        home_view.show_user_interface(conn)

if __name__ == "__main__":
    main()