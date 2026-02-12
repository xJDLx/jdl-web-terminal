import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. PAGE CONFIG
st.set_page_config(page_title="JDL System", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# 2. THEME ENGINE
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if st.session_state.theme == "Light":
    # FORCE LIGHT MODE CSS
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
    # FORCE DARK MODE CSS
    st.markdown("""
        <style>
        /* Default Streamlit Dark Mode is usually fine, but we enforce Tab styling */
        .stTabs [data-baseweb="tab-list"] {background-color: #0e1117;}
        .stTabs [data-baseweb="tab"] {background-color: #0e1117; color: #b2b2b2;}
        .stTabs [aria-selected="true"] {color: #00ff41; border-bottom-color: #00ff41;}
        </style>
    """, unsafe_allow_html=True)

# 3. CONNECTION & ROUTING
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

def main():
    if not st.session_state.admin_verified and not st.session_state.user_verified:
        gatekeeper.show_login(conn)
        return

    if st.session_state.admin_verified:
        t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "🗂️ Registry", "⚙️ Logs", "🔒 Logout"])
        with t1: admin_view.show_dashboard(conn)
        with t2: admin_view.show_catalog_view(conn)
        with t3: st.info("System Normal.")
        with t4:
            if st.button("Logout"):
                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    elif st.session_state.user_verified:
        home_view.show_user_interface(conn)

if __name__ == "__main__":
    main()