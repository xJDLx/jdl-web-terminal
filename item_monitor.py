import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from steamdt_api import SteamdtAPI, load_api_key, save_api_key

def initialize_items_database(conn):
    """Create Items worksheet if it doesn't exist with entry tracking columns"""
    try:
        # Try to read existing Items worksheet
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        try:
            # Create new Items worksheet with specific headers for tracking entries
            headers_df = pd.DataFrame(columns=[
                'Item Name', 'Market Hash Name', 'Added Date', 
                'Entry Price', 'Entry Supply', 'Current Price', 
                'Avg Price (7d)', 'Price Change', 'Status', 'Last Updated'
            ])
            conn.create(worksheet="Items", data=headers_df)
            st.success("✅ Items database created successfully!")
            return True
        except Exception as e:
            st.error(f"Failed to create Items database: {e}")
            return False

def show_add_items_view(conn, api_key: str):
    """Add new items to monitor and capture baseline entry data"""
    st.subheader("Add New Item")
    st.write("📌 Enter the exact item name from Steam Community Market")
    
    api = SteamdtAPI(api_key)
    
    with st.form("add_item_form"):
        market_hash_name = st.text_input(
            "Item Name", 
            placeholder="e.g., AK-47 | Phantom Disruptor (Field-Tested)"
        )
        
        submitted = st.form_submit_button("Add Item to Monitor")
        
        if submitted and market_hash_name:
            with st.spinner("Verifying item and fetching entry metrics..."):
                # Verify item and get current price/meta-data
                price_data = api.get_item_price(market_hash_name)
            
            if price_data is None:
                st.error("❌ Item not found. Please use the exact Steam Market name.")
            else:
                try:
                    # Load existing items
                    try:
                        items_df = conn.read(worksheet="Items", ttl=0)
                        items_df = items_df.dropna(how='all')
                    except:
                        items_df = pd.DataFrame(columns=[
                            'Item Name', 'Market Hash Name', 'Added Date', 
                            'Entry Price', 'Entry Supply', 'Current Price', 
                            'Avg Price (7d)', 'Price Change', 'Status', 'Last Updated'
                        ])
                    
                    # Check for duplicates
                    if not items_df.empty and (items_df['Market Hash Name'].astype(str) == market_hash_name).any():
                        st.error("⚠️ Item is already being tracked")
                        return
                    
                    # Fetch average price and metadata
                    avg_price_data = api.get_average_price(market_hash_name)
                    avg_price = avg_price_data.get('avgPrice', 'N/A') if avg_price_data else 'N/A'
                    
                    # Entry Supply is typically found in the item metadata from Steamdt
                    entry_supply = price_data.get('quantity', 0)
                    current_val = price_data.get('price', 0)

                    # Create record with fixed Entry values that won't change on refresh
                    new_item = {
                        'Item Name': market_hash_name,
                        'Market Hash Name': market_hash_name,
                        'Added Date': datetime.now().strftime("%Y-%m-%d"),
                        'Entry Price': current_val,
                        'Entry Supply': entry_supply,
                        'Current Price': current_val,
                        'Avg Price (7d)': avg_price,
                        'Price Change': '0%',
                        'Status': 'Active',
                        'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)
                    conn.update(worksheet="Items", data=items_df)
                    st.success(f"✅ Added {market_hash_name} (Price: {current_val}, Supply: {entry_supply})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding item: {e}")