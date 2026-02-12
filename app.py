import streamlit as st
from streamlit_gsheets import GSheetsConnection
import gatekeeper
import admin_view
import home_view

# 1. SETUP
st.set_page_config(page_title="JDL Terminal", page_icon="📟", layout="wide")

# 2. SAFE SECRET LOADING
# Using .get() prevents the KeyError if the secret is missing
MASTER_KEY = st.secrets.get("MASTER_KEY", "jdl_default_2026")

# 3. INITIALIZE SESSION STATE
# This prevents KeyErrors in other files
if "user_verified" not in st.session_state:
    st.session_state.user_verified = False
if "admin_verified" not in st.session_state:
    st.session_state.admin_verified = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Guest"

# 4. PERSISTENCE CHECK
if "u" in st.query_params:
    st.session_state.user_verified = True

# 5. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 6. ROUTING
if st.session_state.admin_verified:
    admin_view.show_dashboard(conn)
elif st.session_state.user_verified:
    home_view.show_home()
else:
    gatekeeper.show_login(conn)