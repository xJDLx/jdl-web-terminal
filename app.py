import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. SETUP
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 2. INITIALIZE STATES
if "admin_verified" not in st.session_state:
    st.session_state.admin_verified = False
if "user_verified" not in st.session_state:
    st.session_state.user_verified = False

# 3. REFRESH PROTECTION (READ URL)
# Check if an admin or user is remembered in the URL
if st.query_params.get("role") == "admin":
    st.session_state.admin_verified = True
elif st.query_params.get("role") == "user":
    st.session_state.user_verified = True
    st.session_state.user_name = st.query_params.get("name", "Member")

# 4. ROUTING LOGIC
if st.session_state.admin_verified:
    admin_view.show_dashboard(conn)
elif st.session_state.user_verified:
    home_view.show_home()
else:
    gatekeeper.show_login(conn)