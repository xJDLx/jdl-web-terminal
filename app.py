import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# Setup
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# Session States
if "user_verified" not in st.session_state: st.session_state.user_verified = False
if "admin_verified" not in st.session_state: st.session_state.admin_verified = False

# Navigation Routing
if st.session_state.admin_verified:
    admin_view.show_dashboard(conn)
elif st.session_state.user_verified:
    home_view.show_home()
else:
    gatekeeper.show_login(conn)