import streamlit as st
from datetime import datetime, timedelta

def show_dashboard(conn):
    st.title("👥 Admin Control")
    df = conn.read(worksheet="Sheet1", ttl=0)
    st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Approve & Set Access Time")
    
    if not df.empty:
        target = st.selectbox("Select Pending User", df[df['Status'] == 'Pending']['Name'].tolist())
        # Admin picks the access duration
        days = st.number_input("Grant Access for (Days):", min_value=1, value=30)
        
        if st.button("Approve & Set Time"):
            new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            df.loc[df['Name'] == target, 'Status'] = "Approved"
            df.loc[df['Name'] == target, 'Expiry'] = new_expiry
            conn.update(worksheet="Sheet1", data=df)
            st.success(f"{target} approved until {new_expiry}")
            st.rerun()