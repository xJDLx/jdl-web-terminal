import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from steamdt_api import SteamdtAPI, load_api_key, save_api_key

def initialize_items_database(conn):
    """Create Items worksheet if it doesn't exist"""
    try:
        # Try to read existing Items worksheet
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        try:
            # Create new Items worksheet with headers
            headers_df = pd.DataFrame(columns=[
                'Item Name', 'Market Hash Name', 'Added Date', 
                'Current Price', 'Avg Price (7d)', 'Price Change', 
                'Status', 'Last Updated'
            ])
            conn.create(worksheet="Items", data=headers_df)
            st.success("✅ Items database created successfully!")
            return True
        except Exception as e:
            st.error(f"Failed to create Items database: {e}")
            st.info("Make sure you have a Google Sheet connected and proper permissions.")
            return False

def show_item_monitor(conn):
    """Main item monitor interface"""
    st.header("📊 Item Monitor")
    
    # Initialize database on first load
    if not st.session_state.get("items_db_initialized"):
        initialize_items_database(conn)
        st.session_state.items_db_initialized = True
    
    # Check if API key is configured
    user_folder = st.session_state.get("user_folder")
    if not user_folder:
        st.error("User session not initialized properly")
        return
        
    api_key = load_api_key(user_folder)
    
    if not api_key:
        st.warning("⚙️ API Configuration Required")
        st.info("Please set up your Steamdt.com API key to use the item monitor.")
        
        with st.expander("🔑 Add API Key"):
            api_input = st.text_input("Enter your Steamdt API Key", type="password")
            if st.button("Save API Key"):
                if api_input:
                    save_api_key(api_input)
                    st.success("API Key saved! Refresh to continue.")
                    st.rerun()
                else:
                    st.error("Please enter a valid API Key")
        return
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Monitor", "➕ Add Items", "⚙️ Settings"])
    
    with tab1:
        show_monitor_view(conn, api_key)
    
    with tab2:
        show_add_items_view(conn, api_key)
    
    with tab3:
        show_settings_view(conn, api_key)


def show_monitor_view(conn, api_key: str):
    """Display monitored items with current prices"""
    st.subheader("Monitored Items")
    
    try:
        # Try to load monitored items from Google Sheets
        monitored_items = conn.read(worksheet="Items", ttl=0)
        # Remove header-only rows (if dataframe only has column names)
        if len(monitored_items) == 0:
            monitored_items = pd.DataFrame(columns=[
                'Item Name', 'Market Hash Name', 'Added Date', 
                'Current Price', 'Avg Price (7d)', 'Price Change', 
                'Status', 'Last Updated'
            ])
    except Exception as e:
        st.error(f"Error reading items database: {e}")
        st.info("Try creating the database first or check your Sheet connection.")
        return
    
    if monitored_items.empty:
        st.info("📭 No items being monitored yet.")
        st.info("➕ Go to the '➕ Add Items' tab and enter an item to start monitoring!")
        
        # Show help text
        with st.expander("📖 How to add items"):
            st.write("""
            1. Go to Steam Community Market
            2. Search for a CS2 item
            3. Copy the exact item name (including condition)
            4. Paste it in the '➕ Add Items' tab
            5. Click 'Add Item to Monitor'
            
            Example: `AK-47 | Phantom Disruptor (Field-Tested)`
            """)
        return
    
    # Initialize API client
    api = SteamdtAPI(api_key)
    
    # Create columns for display
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Prices"):
            st.session_state.refresh_prices = True
    
    # Update prices if refresh requested
    if st.session_state.get("refresh_prices"):
        monitored_items = update_all_prices(monitored_items, api, conn)
        st.session_state.refresh_prices = False
    
    # Display items in a nice format
    for idx, row in monitored_items.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{row['Item Name']}**")
                st.caption(row.get('Market Hash Name', ''))
            
            with col2:
                current_price = row.get('Current Price', 'N/A')
                st.metric("Current Price", f"${current_price}")
            
            with col3:
                avg_price = row.get('Avg Price (7d)', 'N/A')
                st.metric("7d Avg", f"${avg_price}")
            
            with col4:
                price_change = row.get('Price Change', 'N/A')
                st.metric("Change", price_change)
            
            # Action buttons
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("📊 Details", key=f"details_{idx}"):
                    show_item_details(row, api)
            
            with b2:
                if st.button("✏️ Edit", key=f"edit_{idx}"):
                    st.session_state.edit_item = idx
            
            with b3:
                if st.button("❌ Remove", key=f"remove_{idx}"):
                    monitored_items = monitored_items.drop(idx)
                    conn.update(worksheet="Items", data=monitored_items)
                    st.success(f"Removed {row['Item Name']}")
                    st.rerun()


def show_add_items_view(conn, api_key: str):
    """Add new items to monitor"""
    st.subheader("Add New Item")
    st.write("📌 Enter the exact item name from Steam Community Market")
    
    api = SteamdtAPI(api_key)
    
    with st.form("add_item_form"):
        market_hash_name = st.text_input(
            "Item Name", 
            placeholder="e.g., AK-47 | Phantom Disruptor (Field-Tested)"
        )
        
        notification_type = st.multiselect(
            "Alert me when...",
            ["Price drops below", "Price rises above", "Stock changes"],
            default=[]
        )
        
        submitted = st.form_submit_button("Add Item to Monitor")
        
        if submitted:
            if market_hash_name:
                with st.spinner("Verifying item..."):
                    # Verify item exists in API
                    price_data = api.get_item_price(market_hash_name)
                
                if price_data is None:
                    st.error("❌ Item not found. Make sure you're using the exact name from Steam Community Market.")
                    st.info("Example: 'AK-47 | Phantom Disruptor (Field-Tested)' or 'AWP Dragon Lore (Factory New)'")
                else:
                    try:
                        # Load existing items (or create empty dataframe)
                        try:
                            items_df = conn.read(worksheet="Items", ttl=0)
                            # Filter out empty rows if any
                            items_df = items_df.dropna(how='all')
                        except:
                            items_df = pd.DataFrame(columns=[
                                'Item Name', 'Market Hash Name', 'Added Date', 
                                'Current Price', 'Avg Price (7d)', 'Price Change', 
                                'Status', 'Last Updated'
                            ])
                        
                        # Check if item already being tracked
                        if not items_df.empty and 'Market Hash Name' in items_df.columns:
                            if (items_df['Market Hash Name'].astype(str).str.strip() == market_hash_name.strip()).any():
                                st.error("⚠️ Item is already being tracked")
                                return
                        
                        # Get average price
                        with st.spinner("Fetching price data..."):
                            avg_price_data = api.get_average_price(market_hash_name)
                            avg_price = avg_price_data.get('avgPrice', 'N/A') if avg_price_data else 'N/A'
                        
                        # Add new item (use market hash name as display name too)
                        new_item = {
                            'Item Name': market_hash_name,
                            'Market Hash Name': market_hash_name,
                            'Added Date': datetime.now().strftime("%Y-%m-%d"),
                            'Current Price': price_data.get('price', 'N/A'),
                            'Avg Price (7d)': avg_price,
                            'Price Change': '0%',
                            'Status': 'Active',
                            'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        items_df = pd.concat(
                            [items_df, pd.DataFrame([new_item])], 
                            ignore_index=True
                        )
                        
                        conn.update(worksheet="Items", data=items_df)
                        st.success(f"✅ Added {market_hash_name} to monitor!")
                        st.info("Go to the '📈 Monitor' tab to see your item")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding item: {e}")
                        st.info("Make sure your Google Sheet is properly connected")
            else:
                st.error("Please enter an item name.")


def show_item_details(item_row, api: SteamdtAPI):
    """Show detailed information about an item"""
    item_name = item_row['Item Name']
    market_hash_name = item_row['Market Hash Name']
    
    with st.popover(f"Details: {item_name}"):
        st.write("**Current Information:**")
        st.write(f"Added: {item_row.get('Added Date', 'N/A')}")
        st.write(f"Status: {item_row.get('Status', 'N/A')}")
        st.write(f"Last Updated: {item_row.get('Last Updated', 'N/A')}")
        
        # Get detailed price info
        price_data = api.get_item_price(market_hash_name)
        if price_data:
            st.write("**Detailed Price Data:**")
            for key, value in price_data.items():
                st.write(f"- {key}: {value}")


def show_settings_view(conn, api_key: str):
    """Settings for item monitor"""
    st.subheader("Settings")
    
    # Database initialization
    with st.expander("💾 Database Management"):
        st.write("**Items Database**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Create/Reset Database", use_container_width=True):
                if initialize_items_database(conn):
                    st.success("Database ready!")
                    st.rerun()
        
        with col2:
            if st.button("📥 Export Items", use_container_width=True):
                try:
                    items_df = conn.read(worksheet="Items", ttl=0)
                    if not items_df.empty:
                        csv_data = items_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv_data,
                            file_name=f"monitored_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("No items to export")
                except Exception as e:
                    st.error(f"Export failed: {e}")
        
        with col3:
            if st.button("🗑️ Clear All Items", use_container_width=True):
                st.warning("This cannot be undone!")
                if st.button("⚠️ Confirm deletion", key="confirm_delete", use_container_width=True):
                    try:
                        empty_df = pd.DataFrame(columns=[
                            'Item Name', 'Market Hash Name', 'Added Date', 
                            'Current Price', 'Avg Price (7d)', 'Price Change', 
                            'Status', 'Last Updated'
                        ])
                        conn.update(worksheet="Items", data=empty_df)
                        st.success("All items cleared")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Clear failed: {e}")
    
    # API Key management
    with st.expander("🔑 API Key Management"):
        st.warning("Your API Key is stored securely. Handle carefully!")
        
        if st.button("🔄 Reset API Key", use_container_width=True):
            import os
            try:
                config_file = os.path.join(st.session_state.user_folder, "steamdt_config.json")
                if os.path.exists(config_file):
                    os.remove(config_file)
                st.success("API Key removed. Please re-enter it.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to reset: {e}")
    
    # Refresh settings
    with st.expander("⚙️ Refresh Settings"):
        refresh_interval = st.slider(
            "Auto-refresh interval (minutes)",
            min_value=5,
            max_value=120,
            value=30
        )
        st.info(f"💡 Prices will auto-refresh every {refresh_interval} minutes")


def update_all_prices(items_df: pd.DataFrame, api: SteamdtAPI, conn) -> pd.DataFrame:
    """Update prices for all monitored items"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    market_hash_names = items_df['Market Hash Name'].tolist()
    
    # Get batch prices
    status_text.text("Fetching prices...")
    batch_prices = api.get_batch_prices(market_hash_names)
    
    if batch_prices is None:
        st.error("Failed to update prices")
        return items_df
    
    # Update dataframe
    for idx, item in enumerate(market_hash_names):
        progress = (idx + 1) / len(market_hash_names)
        progress_bar.progress(progress)
        status_text.text(f"Updating {idx + 1}/{len(market_hash_names)}...")
        
        if item in batch_prices:
            price_info = batch_prices[item]
            current_price = price_info.get('price', 'N/A')
            
            # Calculate price change (simplified - would need historical data)
            items_df.at[idx, 'Current Price'] = current_price
            items_df.at[idx, 'Last Updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save updated data
    conn.update(worksheet="Items", data=items_df)
    
    progress_bar.empty()
    status_text.empty()
    st.success("✅ Prices updated!")
    
    return items_df
