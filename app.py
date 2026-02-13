import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
import os
import datetime
import urllib.parse

# ... (Previous imports and Page Config remain same)

def load_portfolio(user_email):
    # Simplified column structure matching the new database
    cols = [
        "Item Name", "Current Price (CNY)", 
        "24h Price Change (%)", "7d Price Change (%)", 
        "Added Date", "Last Updated"
    ]
    path = get_user_portfolio_path(user_email)
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            # Ensure only requested columns exist
            for c in cols:
                if c not in df.columns: df[c] = 0.0 if "%" in c else ""
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

# Update fetch function to ignore entry/volume logic
def fetch_steamdt_market_data(item_hash, api_key):
    try:
        encoded_name = urllib.parse.quote(item_hash)
        headers = {"Authorization": f"Bearer {api_key}"}
        url = f"https://open.steamdt.com/open/cs2/v1/price/single?marketHashName={encoded_name}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            item_meta = res.get("item", {})
            if not data: return None, "No data"
            
            buff_data = next((m for m in data if m['platform'] == "BUFF"), data[0])
            
            return {
                "price": buff_data.get('sellPrice', 0),
                "p_24h": item_meta.get('price24hChange', 0.0),
                "p_7d": item_meta.get('price7dChange', 0.0),
                "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }, None
        return None, f"HTTP {r.status_code}"
    except Exception as e: return None, str(e)

# In user_dashboard loop, update the row creation
# (Replace the relevant snippet inside user_dashboard)
if st.button("✅ Add Selected"):
    data, err = fetch_steamdt_market_data(selected_item, st.session_state.api_key)
    if data and data['price'] != 0:
        new_row = pd.DataFrame([{
            "Item Name": selected_item,
            "Current Price (CNY)": data['price'],
            "24h Price Change (%)": data['p_24h'],
            "7d Price Change (%)": data['p_7d'],
            "Added Date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "Last Updated": data['updated']
        }])
        df_updated = pd.concat([df_raw, new_row], ignore_index=True)
        save_portfolio(user_email, df_updated)
        st.rerun()