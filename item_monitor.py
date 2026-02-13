import streamlit as st
import pandas as pd
from datetime import datetime
import json
from steamdt_api import SteamdtAPI, load_api_key, save_api_key

def initialize_items_database(conn):
    """Create Items worksheet if it doesn't exist with simplified columns"""
    try:
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        try:
            # Simplified headers: Removed Entry Price, Entry Supply, and Daily Volume
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
            return False

def show_add_items_view(conn, api_key: str):
    """Add new items focused only on current market status"""
    st.subheader("Add New Item")
    api = SteamdtAPI(api_key)
    
    with st.form("add_item_form"):
        market_hash_name = st.text_input(
            "Item Name", 
            placeholder="e.g., AK-47 | Phantom Disruptor (Field-Tested)"
        )
        submitted = st.form_submit_button("Add Item to Monitor")
        
        if submitted and market_hash_name:
            with st.spinner("Fetching data..."):
                price_data = api.get_item_price(market_hash_name)
                
                if price_data:
                    current_price = price_data.get('price', 0)
                    
                    if current_price == 0:
                        st.error("❌ Cannot add item: API returned 0 for price.")
                        return

                    try:
                        items_df = conn.read(worksheet="Items", ttl=0)
                        items_df = items_df.dropna(how='all')
                    except:
                        items_df = pd.DataFrame(columns=[
                            'Item Name', 'Market Hash Name', 'Added Date', 
                            'Current Price', 'Avg Price (7d)', 'Price Change', 
                            'Status', 'Last Updated'
                        ])

                    new_item = {
                        'Item Name': market_hash_name,
                        'Market Hash Name': market_hash_name,
                        'Added Date': datetime.now().strftime("%Y-%m-%d"),
                        'Current Price': current_price,
                        'Avg Price (7d)': 'N/A',
                        'Price Change': '0%',
                        'Status': 'Active',
                        'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)
                    items_df = items_df[items_df['Current Price'] != 0]
                    
                    conn.update(worksheet="Items", data=items_df)
                    st.success(f"✅ Added {market_hash_name}")
                    st.rerun()
                else:
                    st.error("❌ API returned no data.")