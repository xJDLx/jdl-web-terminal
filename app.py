import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. SETUP
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 2. SESSION PERSISTENCE
# Check if a user is already "remembered" in the URL
if "u" in st.query_params:
    st.session_state.user_verified = True
    st.session_state.user_email = st.query_params["u"]

if "admin_auth" in st.query_params and st.query_params["admin_auth"] == st.secrets["MASTER_KEY"]:
    st.session_state.admin_verified = True

# Initialize state if not present
if "user_verified" not in st.session_state: st.session_state.user_verified = False
if "admin_verified" not in st.session_state: st.session_state.admin_verified = False

# 3. ROUTING
if st.session_state.admin_verified:
    admin_view.show_dashboard(conn)
elif st.session_state.user_verified:
    home_view.show_home()
else:
    gatekeeper.show_login(conn)