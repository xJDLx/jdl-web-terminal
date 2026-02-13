import streamlit as st
import pandas as pd
from datetime import datetime
from steamdt_api import SteamdtAPI, load_api_key

def initialize_items_database(conn):
    try:
        conn.read(worksheet="Items", ttl=0)
        return True
    except:
        headers_df = pd.DataFrame(columns=['Item Name', 'Added Date', 'AT Price', 'AT Supply', 'Current Price', 'Supply', 'Last Updated'])
        conn.create(worksheet="Items", data=headers_df)
        return True

def show_add_items_view(conn, api_key: str):
    st.subheader("Add New Item")
    with st.form("add_item_form"):
        name = st.text_input("Item Name")
        if st.form_submit_button("Add Item"):
            from app import fetch_market_data
            init, _ = fetch_market_data(name, api_key)
            if init:
                items_df = conn.read(worksheet="Items", ttl=0)
                new_item = {
                    'Item Name': name, 'Added Date': datetime.now().strftime("%Y-%m-%d"),
                    'AT Price': init["price"], 'AT Supply': init["supply"],
                    'Current Price': init["price"], 'Supply': init["supply"],
                    'Last Updated': init["updated"]
                }
                items_df = pd.concat([items_df, pd.DataFrame([new_item])], ignore_index=True)
                conn.update(worksheet="Items", data=items_df)
                st.rerun()