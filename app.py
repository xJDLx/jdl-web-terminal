import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu # The Navbar Library
import gatekeeper
import admin_view
import home_view

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="JDL System", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="collapsed" # Hide the side bar to focus on Top Nav
)

# 2. CSS STYLING (To make the Navbar look built-in)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;} /* Pull content up */
    </style>
""", unsafe_allow_html=True)

# 3. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 4. SESSION STATE INIT
if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

# 5. REFRESH LOGIC
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

def main():
    # --- LOGGED OUT? SHOW LOGIN ---
    if not st.session_state.admin_verified and not st.session_state.user_verified:
        gatekeeper.show_login(conn)
        return

    # --- THE NAVBAR (Top Navigation) ---
    # This is the "Option Menu" that acts as your main controller
    selected = option_menu(
        menu_title=None, 
        options=["Dashboard", "Registry", "System Logs", "Logout"], 
        icons=["speedometer2", "table", "terminal", "box-arrow-right"], 
        menu_icon="cast", 
        default_index=0, 
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#0e1117"},
            "icon": {"color": "#00ff41", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "center", "margin":"0px", "--hover-color": "#262730"},
            "nav-link-selected": {"background-color": "#262730", "color": "#00ff41", "border-bottom": "2px solid #00ff41"},
        }
    )

    # --- NAVIGATION LOGIC ---
    if selected == "Logout":
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    # ADMIN VIEWS
    if st.session_state.admin_verified:
        if selected == "Dashboard":
            admin_view.show_dashboard(conn)
        elif selected == "Registry":
            admin_view.show_catalog_view(conn) # You'll need to ensure this function exists in admin_view
        elif selected == "System Logs":
            st.title("📟 System Event Logs")