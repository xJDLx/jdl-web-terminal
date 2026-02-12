import streamlit as st
from datetime import datetime, timedelta

def show_dashboard(conn):
    # Header and Logout
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.title("👥 Admin Control Center")
    with col2:
        if st.button("🔒 Admin Logout"):
            st.query_params.clear()
            st.session_state.admin_verified = False
            st.rerun()

    # Sync Controls
    if st.button("🔄 Force Data Refresh"):
        st.cache_data.clear()
        st.rerun()

    try:
        # Load the raw data
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        # Cleanup: Remove completely empty rows
        df = df.dropna(subset=['Email'])

        # Data Metrics
        st.subheader("System Overview")
        m1, m2 = st.columns(2)
        m1.metric("Total Entries", len(df))
        m2.metric("Pending Requests", len(df[df['Status'] == 'Pending']))

        # Search Bar
        search = st.text_input("🔍 Search Users by Name or Email").lower()
        if search:
            df = df[df['Name'].str.lower().contains(search) | df['Email'].str.lower().contains(search)]

        # The Table
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Manage Pending Requests")
        
        # Filter for logic
        pending_names = df[df['Status'] == 'Pending']['Name'].tolist()
        
        if pending_names:
            target = st.selectbox("Select User to Approve", pending_names)
            days = st.number_input("Grant Access (Days):", min_value=1, value=30)
            
            if st.button("Approve & Set Expiry"):
                # Calculate new date
                new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                
                # Update the specific row
                df.loc[df['Name'] == target, 'Status'] = "Approved"
                df.loc[df['Name'] == target, 'Expiry'] = new_expiry
                
                # Push back to Google Sheets
                conn.update(worksheet="Sheet1", data=df)
                st.success(f"SUCCESS: {target} is now Approved until {new_expiry}")
                st.rerun()
        else:
            st.info("No active pending requests.")

    except Exception as e:
        st.error("⚠️ Data Load Error")
        st.write(f"The app couldn't read your sheet. Error: {e}")
        st.info("Ensure your Google Sheet headers are exactly: Name, Email, Password, Date, Status, Expiry, Last Login, Session")