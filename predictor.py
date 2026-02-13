import streamlit as st
import pandas as pd
import numpy as np

def get_prediction_score(row, weights, price_col, supply_col):
    # Ensure values are numeric to avoid crashes
    c_price, c_supply = float(row.get('Current Price', 0)), float(row.get('Supply', 0))
    e_price, e_supply = float(row.get(price_col, 0)), float(row.get(supply_col, 0))
    
    if e_supply == 0 or e_price == 0: return {'score': 0, 'signal': '⚖️ NEUTRAL'}
    
    supply_pct = (e_supply - c_supply) / e_supply
    abs_pts = np.clip(supply_pct * 1000, 0, 100)
    
    price_pct = (c_price - e_price) / e_price
    div_pts = np.clip((supply_pct - price_pct) * 500, 0, 100) if (supply_pct - price_pct) > 0 else 0
    
    total = round((abs_pts * weights['abs']) + (div_pts * weights['div']), 1)
    return {'score': total, 'signal': "🥇 PUMP READY" if total >= 80 else "⚖️ NEUTRAL"}

def show_predictor_view(conn, view_type="Permanent"):
    try:
        items_df = conn.read(worksheet="Items", ttl=0)
    except:
        st.info("No items found.")
        return
        
    weights = {'abs': st.session_state.get('w_abs', 0.4), 'div': st.session_state.get('w_div', 0.3)}
    p_col, s_col = ("AT Price", "AT Supply") if view_type == "Permanent" else ("Sess Price", "Sess Supply")
    
    if not items_df.empty:
        results = [get_prediction_score(row, weights, p_col, s_col) for _, row in items_df.iterrows()]
        # Display logic continues here...