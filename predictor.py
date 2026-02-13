import streamlit as st
import pandas as pd
import numpy as np

def get_prediction_score(row, weights, price_col, supply_col):
    c_price, c_supply = float(row['Current Price']), float(row['Supply'])
    e_price, e_supply = float(row[price_col]), float(row[supply_col])
    
    supply_pct = (e_supply - c_supply) / max(1, e_supply)
    abs_pts = np.clip(supply_pct * 1000, 0, 100)
    
    price_pct = (c_price - e_price) / max(1, e_price)
    div_pts = np.clip((supply_pct - price_pct) * 500, 0, 100) if (supply_pct - price_pct) > 0 else 0
    
    total = round((abs_pts * weights['abs']) + (div_pts * weights['div']), 1)
    return {'score': total, 'signal': "🥇 PUMP READY" if total >= 80 else "⚖️ NEUTRAL"}

def show_predictor_view(conn, view_type="Permanent"):
    items_df = conn.read(worksheet="Items", ttl=0)
    weights = {'abs': st.session_state.get('w_abs', 0.4), 'div': st.session_state.get('w_div', 0.3)}
    p_col, s_col = ("AT Price", "AT Supply") if view_type == "Permanent" else ("Sess Price", "Sess Supply")
    
    results = [get_prediction_score(row, weights, p_col, s_col) for _, row in items_df.iterrows()]
    # Display Logic...