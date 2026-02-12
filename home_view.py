import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime
import item_monitor

# --- 1. HEARTBEAT & EXPIRY ---
def run_heartbeat(conn):
    if st.session_state.get("admin_verified"): return "Active"

    email_param = st.query_params.get("u")
    if not email_param: return "No Email"

    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.fillna("")
        
        # SMART MATCH: Clean both sides to ensure they match
        clean_param = email_param.strip().lower()
        # Create a temporary column for matching so we don't break original data
        match_series = df['Email'].astype(str).str.strip().str.lower()
        
        if clean_param in match_series.values:
            # Find the true index in the original dataframe
            idx = match_series[match_series == clean_param].index[0]
            user_row = df.iloc[idx]
            
            # Check Expiry
            expiry_str = str(user_row.get('Expiry', ''))
            if expiry_str and expiry_str.strip() != "":
                try:
                    expiry_date = pd.to_datetime(expiry_str)
                    if datetime.now() > expiry_date:
                        return "Expired"
                except: pass

            # Update Online Status
            if "status_checked" not in st.session_state:
                df.at[idx, 'Session'] = "Online"
                df.at[idx, 'Last Login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.update(worksheet="Sheet1", data=df)
                st.session_state.status_checked = True
            
            return "Active"
            
    except Exception as e:
        print(f"Heartbeat Error: {e}")
        return "Active"
    
    return "Active"

# --- 2. TABS ---

def tab_overview(conn, email):
    user = st.session_state.get('user_name', 'Agent')
    if st.session_state.get("admin_verified"): user = "Admin (Preview)"
    
    st.header(f"👋 Welcome, {user}")
    
    days_left = "∞"
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        # Smart Match for Display
        clean_email = email.strip().lower()
        match = df[df['Email'].astype(str).str.strip().str.lower() == clean_email]
        if not match.empty:
            expiry_str = str(match.iloc[0].get('Expiry', ''))
            if expiry_str and expiry_str != "":
                exp_date = pd.to_datetime(expiry_str)
                delta = exp_date - datetime.now()
                days_left = f"{delta.days} Days"
    except: pass

    st.info("System Status: 🟢 ONLINE")
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscription", days_left)
    c2.metric("Efficiency", "98%")
    c3.metric("Tasks", "5")

def tab_predictions(conn):
    st.header("🔮 AI Predictions")
    
    # Add new prediction form
    with st.expander("➕ Add New Prediction"):
        try:
            # Get the directory of the current file and construct path to JSON
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, 'csgo_api_v47.json')
            
            with open(json_path, 'r') as f:
                api_data = json.load(f)
                
            # Extract relevant CSGO data
            teams = []
            matches = []
            for match in api_data.get('matches', []):
                team1 = match.get('team1', {}).get('name', '')
                team2 = match.get('team2', {}).get('name', '')
                if team1 and team1 not in teams:
                    teams.append(team1)
                if team2 and team2 not in teams:
                    teams.append(team2)
                matches.append(f"{team1} vs {team2}")

            with st.form("new_prediction"):
                match = st.selectbox("Select Match", matches)
                prediction_type = st.selectbox("Prediction Type", 
                    ["Match Winner", "Total Rounds", "First Half Winner"])
                team_choice = st.selectbox("Team Selection", teams) if prediction_type != "Total Rounds" else None
                confidence = st.slider("Confidence", 0, 100, 50)
                
                # Build title and description based on selections
                title = f"CSGO: {match}"
                description = f"Prediction: {prediction_type}"
                if team_choice:
                    description += f" - {team_choice}"
                
                status = "Active"  # Default for new predictions
                
                submitted = st.form_submit_button("Submit Prediction")
                
                if submitted and title and description:
                    try:
                        # Get existing predictions or create new DataFrame
                        try:
                            predictions_df = conn.read(worksheet="Predictions", ttl=0)
                        except:
                            predictions_df = pd.DataFrame(columns=['Title', 'Description', 'Status', 'Confidence', 'Date', 'Accuracy'])
                        
                        # Add new prediction
                        new_row = {
                            'Title': title,
                            'Description': description,
                            'Status': status,
                            'Confidence': f"{confidence}",
                            'Date': datetime.now().strftime("%Y-%m-%d"),
                            'Accuracy': '0'
                        }
                        predictions_df = pd.concat([predictions_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        # Update the sheet
                        conn.update(worksheet="Predictions", data=predictions_df)
                        st.success("Prediction added successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error adding prediction: {e}")
        except FileNotFoundError:
            st.error("Required API file not found: csgo_api_v47.json")
        except json.JSONDecodeError:
            st.error("Error reading API file: Invalid JSON format")
    
    # Display existing predictions
    try:
        predictions_df = conn.read(worksheet="Predictions", ttl=0)
        predictions_df = predictions_df.fillna("")
        
        if predictions_df.empty:
            st.info("No predictions available yet.")
        else:
            for index, row in predictions_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.subheader(f"📊 {row.get('Title', 'Untitled')}")
                        st.write(row.get('Description', ''))
                        
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        meta_col1.caption(f"Status: {row.get('Status', 'Active')}")
                        meta_col2.caption(f"Confidence: {row.get('Confidence', 'N/A')}")
                        meta_col3.caption(f"Date: {row.get('Date', 'N/A')}")
                    
                    with col2:
                        st.metric("Accuracy", f"{row.get('Accuracy', '0')}%")
    
    except Exception as e:
        st.error(f"Error loading predictions: {e}")

def tab_inventory(conn):
    st.header("📦 Inventory Database")
    
    try:
        # Load CSGO API data
        with open('csgo_api_v47.json', 'r') as f:
            api_data = json.load(f)
        
        # Add new item form
        with st.expander("➕ Add New Item"):
            with st.form("new_item"):
                # Get available items from API
                items = []
                for item in api_data.get('items', []):
                    item_name = item.get('name', '')
                    if item_name:
                        items.append(item_name)
                
                selected_item = st.selectbox("Select Item", items)
                entry_price = st.number_input("Entry Price", min_value=0.0, step=0.01)
                current_price = st.number_input("Current Price", min_value=0.0, step=0.01)
                
                # Calculate differences
                price_diff = current_price - entry_price
                price_percentage = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                
                # Get supply from API
                supply = next((item.get('supply', 0) for item in api_data.get('items', []) 
                             if item.get('name') == selected_item), 0)
                
                submitted = st.form_submit_button("Add Item")
                
                if submitted and selected_item:
                    try:
                        # Create or load existing inventory
                        try:
                            inventory_df = conn.read(worksheet="Inventory", ttl=0)
                        except:
                            inventory_df = pd.DataFrame(columns=[
                                'Item Name', 'Entry Price', 'Current Price', 
                                'Price Difference', 'Price %', 'Supply'
                            ])
                        
                        # Add new item
                        new_row = {
                            'Item Name': selected_item,
                            'Entry Price': f"${entry_price:.2f}",
                            'Current Price': f"${current_price:.2f}",
                            'Price Difference': f"${price_diff:.2f}",
                            'Price %': f"{price_percentage:.1f}%",
                            'Supply': supply
                        }
                        inventory_df = pd.concat([inventory_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        # Update the sheet
                        conn.update(worksheet="Inventory", data=inventory_df)
                        st.success("Item added successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error adding item: {e}")
        
        # Display inventory
        try:
            inventory_df = conn.read(worksheet="Inventory", ttl=0)
            if not inventory_df.empty:
                st.dataframe(inventory_df, use_container_width=True, hide_index=True)
            else:
                st.info("No items in inventory yet.")
        except Exception as e:
            st.info("📋 Inventory database not yet configured. Add your first item above.")
            
    except FileNotFoundError:
        st.error("Required API file not found: csgo_api_v47.json")
    except json.JSONDecodeError:
        st.error("Error reading API file: Invalid JSON format")

def tab_settings(conn):
    st.header("⚙️ Settings")
    
    # --- 🔌 STEAMDT API SECTION ---
    with st.container(border=True):
        st.subheader("🔌 API Configuration")
        
        try:
            df = conn.read(worksheet="Sheet1", ttl=0)
            df = df.fillna("")
            
            # Get Email from URL
            email_param = st.query_params.get("u")
            
            # --- DEBUG INFO (Only shows if something is wrong) ---
            if not email_param:
                st.error("Error: No user email detected in URL.")
                st.stop()
                
            # SMART MATCH LOGIC
            clean_param = email_param.strip().lower()
            match_series = df['Email'].astype(str).str.strip().str.lower()
            
            # Check if user exists
            if clean_param in match_series.values:
                # Get the row index
                idx = match_series[match_series == clean_param].index[0]
                user_row = df.iloc[idx]
                
                # Check current key
                current_key = ""
                if "SteamDT API" in df.columns:
                    val = user_row.get("SteamDT API", "")
                    if pd.notna(val) and str(val) != "nan":
                        current_key = str(val)
                else:
                    # Auto-create column if missing
                    df["SteamDT API"] = ""
                    conn.update(worksheet="Sheet1", data=df)
                    st.rerun()

                # Status
                if current_key: st.caption("Status: 🟢 Key Saved")
                else: st.caption("Status: 🔴 No Key Found")

                # Input
                new_key = st.text_input("SteamDT API Key", value=current_key, type="password")
                
                if st.button("💾 Save API Key"):
                    # Update EXACT row index
                    df.at[idx, "SteamDT API"] = new_key
                    conn.update(worksheet="Sheet1", data=df)
                    st.success("Key Saved Successfully!")
                    st.rerun()
            else:
                st.error(f"User '{email_param}' not found in database.")
                st.write("Debug: available emails ->", df['Email'].tolist())

        except Exception as e:
            st.error(f"Settings Error: {e}")

    st.divider()

    with st.expander("🔐 Security Profile"):
        st.text_input("Email", value=st.query_params.get("u"), disabled=True)
        st.text_input("New Password", type="password")
        if st.button("Update Password"):
            st.toast("Request sent to Admin.")

    st.divider()
    
    if not st.session_state.get("admin_verified"):
        if st.button("🚪 Log Out", type="primary"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

# --- 3. MASTER INTERFACE ---
def show_user_interface(conn):
    status = run_heartbeat(conn)
    if status == "Expired":
        st.error("⛔ Subscription Expired.")
        if st.button("Login"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
        return

    email = st.query_params.get("u")
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "� Item Monitor", "📦 Inventory", "⚙️ Settings"])
    with t1: tab_overview(conn, email)
    with t2: tab_predictions(conn)
    with t3: tab_inventory(conn)
    with t4: tab_settings(conn)
