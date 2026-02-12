import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. PAGE CONFIG
st.set_page_config(page_title="JDL System", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# 2. THEME ENGINE
if "theme" not in st.session_state: st.session_state.theme = "Dark"

if st.session_state.theme == "Light":
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {background-color: #ffffff; color: black;}
        [data-testid="stHeader"] {background-color: #ffffff;}
        [data-testid="stSidebar"] {background-color: #f0f2f6;}
        .stTabs [data-baseweb="tab-list"] {background-color: #ffffff;}
        .stTabs [data-baseweb="tab"] {background-color: #ffffff; color: black;}
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {background-color: #0e1117;}
        .stTabs [data-baseweb="tab"] {background-color: #0e1117; color: #b2b2b2;}
        .stTabs [aria-selected="true"] {color: #00ff41; border-bottom-color: #00ff41;}
        </style>
    """, unsafe_allow_html=True)

# 3. CONNECTION
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
        # NEW: Added "User View" to the tabs
        t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "🗂️ Registry", "👁️ User View", "⚙️ Logs", "🔒 Logout"])
        
        with t1: admin_view.show_dashboard(conn)
        with t2: admin_view.show_catalog_view(conn)
        
        # THIS IS THE SWITCHER TAB
        with t3:
            st.warning("⚠️ You are viewing the User Interface as an Administrator.")
            home_view.show_user_interface(conn)
            
        with t4: st.info("System Normal.")
        with t5:
            if st.button("Logout"):
                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    # --- USER VIEW ---
    elif st.session_state.user_verified:
        home_view.show_user_interface(conn)

if __name__ == "__main__":
    main()