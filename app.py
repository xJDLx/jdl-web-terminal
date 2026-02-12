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

# 2. THEME ENGINE (New Feature)
def apply_theme():
    # Default to Dark if not set
    if "theme" not in st.session_state:
        st.session_state.theme = "Dark"

    # If Light Mode is selected, we force white backgrounds using CSS override
    if st.session_state.theme == "Light":
        st.markdown("""
            <style>
            [data-testid="stAppViewContainer"] {
                background-color: #ffffff !important;
                color: #000000 !important;
            }
            [data-testid="stSidebar"] {
                background-color: #f0f2f6 !important;
            }
            [data-testid="stHeader"] {
                background-color: #ffffff !important;
            }
            .stTabs [data-baseweb="tab-list"] {
                background-color: #ffffff !important;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #ffffff !important;
                color: #000000 !important;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        # DARK MODE (Your Default Professional Look)
        st.markdown("""
            <style>
            .stTabs [data-baseweb="tab-list"] {
                background-color: #0e1117;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #0e1117;
                color: #b2b2b2;
            }
            .stTabs [aria-selected="true"] {
                color: #00ff41 !important;
                border-bottom-color: #00ff41 !important;
            }
            </style>
        """, unsafe_allow_html=True)

# Apply the theme immediately
apply_theme()

# 3. CONNECTION & STATE
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

if "admin_verified" not in st.session_state: st.session_state.admin_verified = False
if "user_verified" not in st.session_state: st.session_state.user_verified = False

# 4. REFRESH LOGIC
if st.query_params.get("role") == "admin": st.session_state.admin_verified = True
elif st.query_params.get("role") == "user": st.session_state.user_verified = True

def main():
    if not st.session_state.admin_verified and not st.session_state.user_verified:
        gatekeeper.show_login(conn)
        return

    # --- ADMIN VIEW ---
    if st.session_state.admin_verified:
        # Add Theme Toggle to Admin Sidebar or Top
        with st.sidebar:
            st.title("⚙️ Preferences")
            # We use radio to switch theme
            theme = st.radio("Theme", ["Dark", "Light"], 
                             index=0 if st.session_state.theme == "Dark" else 1)
            if theme != st.session_state.theme:
                st.session_state.theme = theme
                st.rerun()

        t1, t2, t3, t4 = st.tabs(["📊 Dashboard", "🗂️ Registry", "⚙️ Logs", "🔒 Logout"])
        with t1: admin_view.show_dashboard(conn)
        with t2: admin_view.show_catalog_view(conn)
        with t3: st.info("System Normal.")
        with t4:
            if st.button("Logout"):
                st.query_params.clear()
                st.session_state.clear()
                st.rerun()

    # --- USER VIEW ---
    elif st.session_state.user_verified:
        home_view.show_user_interface(conn)

if __name__ == "__main__":
    main()