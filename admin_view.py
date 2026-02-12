import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_command_center(conn):
    st.title("🛡️ Command Center")
    
    try:
        # 1. FETCH & CLEAN
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # --- 🚨 PENDING REQUESTS ALERT SYSTEM ---
        pending_users = df[df['Status'] == 'Pending']
        
        if not pending_users.empty:
            with st.container(border=True):
                st.error(f"🔔 ACTION REQUIRED: {len(pending_users)} New User Request(s)")
                
                # Loop through each pending user
                for index, row in pending_users.iterrows():
                    st.divider() # Separator between users
                    c1, c2, c3 = st.columns([2, 1.5, 1.5])
                    
                    with c1:
                        st.markdown(f"**{row['Name']}**")
                        st.caption(f"📧 {row['Email']}")
                        
                    with c2:
                        # OPTION 1: Pick Exact Date
                        # Default is Today + 30 Days
                        default_date = datetime.now() + timedelta(days=30)
                        picked_date = st.date_input(
                            "Expiry Date", 
                            value=default_date, 
                            min_value=datetime.now(),
                            key=f"d_{index}", 
                            label_visibility="collapsed"
                        )
                        # OPTION 2: Lifetime Toggle
                        is_lifetime = st.checkbox("♾️ Lifetime Access", key=f"life_{index}")

                    with c3:
                        # APPROVE BUTTON
                        if st.button("✅ Approve", key=f"app_{index}", use_container_width=True):
                            # Logic: Lifetime overrides date picker
                            if is_lifetime:
                                final_expiry = "2099-12-31"
                            else:
                                final_expiry = picked_date.strftime("%Y-%m-%d")
                                
                            df.at[index, 'Status'] = "Approved"
                            df.at[index, 'Session'] = "Offline"
                            df.at[index, 'Expiry'] = final_expiry
                            
                            conn.update(worksheet="Sheet1", data=df)
                            st.success(f"Approved {row['Name']} until {final_expiry}!")
                            st.rerun()

                        # DENY BUTTON
                        if st.button("❌ Deny", key=f"deny_{index}", use_container_width=True):
                            df.at[index, 'Status'] = "Denied"
                            conn.update(worksheet="Sheet1", data=df)
                            st.warning(f"Denied {row['Name']}.")
                            st.rerun()

        # 2. METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Sessions", len(df[df['Session'] == 'Online']))
        c2.metric("Pending", len(pending_users))
        c3.metric("Total Users", len(df))
        c4.metric("System Status", "🟢 Nominal")
        
        st.divider()
        
        # 3. QUICK OPS & SEARCH
        col_actions, col_search = st.columns([0.4, 0.6])
        with col_actions:
            st.subheader("⚡ Quick Ops")
            b1, b2 = st.columns(2)
            if b1.button("🔄 Sync", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            if b2.button("⚠️ Reset Offline", use_container_width=True):
                df['Session'] = "Offline"
                # Clean dates for saving
                save_df = df.copy()
                if 'Expiry' in save_df.columns:
                    save_df['Expiry'] = save_df['Expiry'].astype(str).replace('NaT', '')
                if 'Last Login' in save_df.columns:
                    save_df['Last Login'] = save_df['Last Login'].astype(str).replace('NaT', '')
                conn.update(worksheet="Sheet1", data=save_df)
                st.rerun()

        with col_search:
            st.subheader("🔍 Database Search")
            search = st.text_input("Filter", placeholder="User, Email...", label_visibility="collapsed")

        # 4. FILTER LOGIC
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.divider()
        
        # 6. PREDICTIONS MANAGEMENT SECTION
        st.markdown("### 🔮 Predictions Management")
        
        try:
            # Fetch predictions
            predictions_df = conn.read(worksheet="Predictions", ttl=0)
            predictions_df = predictions_df.fillna("")
        except:
            # Create Predictions worksheet if it doesn't exist
            predictions_df = pd.DataFrame({
                "ID": [],
                "Title": [],
                "Description": [],
                "Status": [],
                "Accuracy": [],
                "Confidence": [],
                "Date": []
            })
        
        # Add new prediction
        with st.expander("➕ Add New Prediction", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                new_title = st.text_input("Prediction Title")
                new_status = st.selectbox("Status", ["Active", "Inactive", "Archived"])
            with col2:
                new_desc = st.text_area("Description")
                new_accuracy = st.slider("Accuracy (%)", 0, 100, 85)
            
            new_confidence = st.selectbox("Confidence Level", ["Low", "Medium", "High"])
            
            if st.button("Add Prediction", type="primary"):
                if new_title:
                    new_row = {
                        "ID": len(predictions_df) + 1,
                        "Title": new_title,
                        "Description": new_desc,
                        "Status": new_status,
                        "Accuracy": new_accuracy,
                        "Confidence": new_confidence,
                        "Date": datetime.now().strftime("%Y-%m-%d")
                    }
                    predictions_df = pd.concat([predictions_df, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(worksheet="Predictions", data=predictions_df)
                    st.success(f"✅ Added prediction: {new_title}")
                    st.rerun()
                else:
                    st.error("Please enter a prediction title.")
        
        # Display and edit predictions
        if not predictions_df.empty:
            st.markdown("#### Current Predictions")
            edited_predictions = st.data_editor(
                predictions_df,
                use_container_width=True,
                height=300,
                num_rows="dynamic",
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Active", "Inactive", "Archived"]),
                    "Confidence": st.column_config.SelectboxColumn("Confidence", options=["Low", "Medium", "High"]),
                    "Accuracy": st.column_config.NumberColumn("Accuracy (%)", min_value=0, max_value=100)
                }
            )
            
            if st.button("💾 Save Predictions", type="primary", use_container_width=True):
                conn.update(worksheet="Predictions", data=edited_predictions)
                st.success("✅ Predictions Updated!")
        else:
            st.info("No predictions yet. Add one to get started!")
        

        
        # Display Logic (Convert to Date objects for the picker)
        if 'Expiry' in df_display.columns:
            df_display['Expiry'] = pd.to_datetime(df_display['Expiry'], errors='coerce')
        if 'Last Login' in df_display.columns:
            df_display['Last Login'] = pd.to_datetime(df_display['Last Login'], errors='coerce')

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=600,
            num_rows="dynamic",
            column_config={
                "Session": st.column_config.SelectboxColumn("Session", options=["Online", "Offline"]),
                "Status": st.column_config.SelectboxColumn("Status", options=["Approved", "Pending", "Denied"]),
                "Password": None, # Hidden
                "Last Login": st.column_config.DatetimeColumn("Last Login", format="D MMM, HH:mm", disabled=True),
                "Expiry": st.column_config.DateColumn("Expiry", format="YYYY-MM-DD")
            }
        )
        
        # SAVE BUTTON
        if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
            # Clean for Google Sheets
            final_df = edited_df.copy()
            if 'Expiry' in final_df.columns:
                final_df['Expiry'] = final_df['Expiry'].astype(str).replace('NaT', '')
            if 'Last Login' in final_df.columns:
                final_df['Last Login'] = final_df['Last Login'].astype(str).replace('NaT', '')
            
            conn.update(worksheet="Sheet1", data=final_df)
            st.success("✅ Database Saved!")

    except Exception as e:
        st.error(f"System Error: {e}")