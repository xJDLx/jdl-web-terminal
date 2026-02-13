import streamlit as st
import pandas as pd
from datetime import datetime
import json
from steamdt_api import SteamdtAPI, load_api_key, save_api_key

def initialize_items_database(conn):
    """Create Items worksheet if it doesn't exist with AT/Sess tracking columns"""
    try:
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        try:
            # Schema aligned with app.py starting supply and price requirements
            headers_df = pd.DataFrame(columns=[
                'Item Name', 'Market Hash Name', 'Added Date', 
                'AT Price', 'AT Supply', 'Current Price', 
                'Current Supply', 'Status', 'Last Updated'
            ])
            conn.create(worksheet="Items", data=headers_df)
            st.success("✅ Items database created successfully!")
            return True
        except Exception as e:
            st.error(f"Failed to create Items database: {e}")
            return False

def show_add_items_view(conn, api_key: str):
    """Add new items and capture starting supply and price baseline"""
    st.subheader("Add New Item")
    api = SteamdtAPI(api_key)
    
    with st.form("add_item_form"):
        market_hash_name = st.text_input("Item Name", placeholder="e.g., AK-47 | Phantom Disruptor (Field-Tested)")
        submitted = st.form_submit_button("Add Item to Monitor")
        
        if submitted and market_hash_name:
            with st.spinner("Fetching starting metrics..."):
                price_data = api.get_item_price(market_hash_name)
                
                if price_data:
                    current_price = price_data.get('price', 0)
                    current_supply = price_data.get('quantity', 0)
                    
                    if current_price == 0:
                        st.error("❌ API returned 0 for price.")
                        return

                    try:
                        items_df = conn.read(worksheet="Items", ttl=0)
                    except:
                        items_df = pd.DataFrame(columns=['Item Name', 'Market Hash Name', 'Added Date', 'AT Price', 'AT Supply', 'Current Price', 'Current Supply', 'Status', 'Last Updated'])

                    new_item = {
                        'Item Name': market_hash_name,
                        'Market Hash Name': market_hash_name,
                        'Added Date': datetime.now().strftime("%Y-%m-%d"),
                        'AT Price': current_price,
                        'AT Supply': current_supply,
                        'Current Price': current_price,
                        'Current Supply': current_supply,
                        'Status': 'Active',
                        'Last Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)
                    conn.update(worksheet="Items", data=items_df)
                    st.success(f"✅ Added {market_hash_name} (Starting Price: {current_price})")
                    st.rerun()
                else:
                    st.error("❌ API returned no data.")