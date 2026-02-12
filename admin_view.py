import streamlit as st

def show_dashboard(conn):
    st.title("👥 Admin Control")
    df = conn.read(worksheet="Sheet1", ttl=0)
    st.dataframe(df, use_container_width=True)
    # (Include your Status Update buttons here)