import streamlit as st
import pandas as pd
from datetime import datetime
import json
from steamdt_api import SteamdtAPI, load_api_key, save_api_key

def initialize_items_database(conn):
    """Create Items worksheet if it doesn't exist"""
    try:
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        try:
            headers_df = pd.DataFrame(columns=[
                'Item Name', 'Market Hash Name', 'Added Date', 
                'Entry Price (CNY)', 'Entry Supply', 'Current Price (CNY)', 
                'Avg Price (7d)', 'Price Change', 'Status', 'Last Updated'
            ])
            conn.create(worksheet="Items", data=headers_df)
            st.success("✅ Items database created successfully!")
            return True
        except Exception as e:
            st.error(f"Failed to create Items database: {e}")
            return False

def show_add_items_view(conn, api_key: str):
    """Add new items and remove any invalid rows with 0 values"""
    st.subheader("Add New Item")
    api = SteamdtAPI(api_key)
    
    with st.form("add_item_form"):
        market_hash_name = st.text_input("Item Name", placeholder="e.g., AK-47 | Phantom Disruptor (Field-Tested)")
        submitted = st.form_submit_button("Add Item to Monitor")
        
        if submitted and market_hash_name:
            with st.spinner("Fetching data..."):
                price_data = api.get_item_price(market_hash_name)
                
                if price_data:
                    current_val = price_data.get('price', 0)
                    entry_supply = price_data.get('quantity', 0)
                    
                    # Validation: Do not add if data is 0
                    if current_val == 0 or entry_supply == 0:
                        st.error("❌ Cannot add item: API returned 0 for price or supply.")
                        return

                    try:
                        items_df = conn.read(worksheet="Items", ttl=0)
                        items_df = items_df.dropna(how='all')
                    except:
                        items_df = pd.DataFrame(columns=['Item Name', 'Market Hash Name', 'Added Date', 'Entry Price (CNY)', 'Entry Supply', 'Current Price (CNY)', 'Avg Price (7d)', 'Price Change', 'Status', 'Last Updated'])

                    new_item = {
                        'Item Name': market_hash_name,
                        'Market Hash Name': market_hash_name,
                        'Added Date': datetime.now().strftime("%Y-%m-%d"),
                        'Entry Price (CNY)': current_val,
                        'Entry Supply': entry_supply,
                        'Current Price (CNY)': current_val,
                        'Avg Price (7d)': 'N/A',
                        'Price Change': '0%',
                        'Status': 'Active',
                        'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)
                    
                    # Clean the dataframe: remove any row that has a 0 in critical columns
                    items_df = items_df[
                        (items_df['Entry Price (CNY)'] != 0) & 
                        (items_df['Entry Supply'] != 0) &
                        (items_df['Current Price (CNY)'] != 0)
                    ]
                    
                    conn.update(worksheet="Items", data=items_df)
                    st.success(f"✅ Added {market_hash_name} and cleaned 0-value rows.")
                    st.rerun()