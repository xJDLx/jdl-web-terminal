import streamlit as st

def show_dashboard(conn):
    st.title("👥 Admin Control Center")
    
    # Sync Button to clear cache
    if st.button("🔄 Sync Live Data"):
        st.cache_data.clear()
        st.rerun()

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        st.subheader("User Database")
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Manage Status")
        if not df.empty:
            target = st.selectbox("Select User", df['Name'].tolist())
            new_stat = st.radio("Set Status", ["Approved", "Denied", "Pending"], horizontal=True)
            if st.button("Update User"):
                df.loc[df['Name'] == target, 'Status'] = new_stat
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"Updated {target} to {new_stat}")
                st.rerun()
    except Exception as e:
        st.error("Data Sync Error. Check your Spreadsheet headers.")