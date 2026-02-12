import streamlit as st
import pandas as pd
import numpy as np
import datetime
import urllib.parse
from steamdt_api import SteamdtAPI, load_api_key

def get_bought_momentum(items_df, item_name):
    """Calculate buying momentum over different time periods"""
    if items_df.empty:
        return 0, 0, 0
    
    item_data = items_df[items_df['Item Name'] == item_name].copy()
    if len(item_data) < 2:
        return 0, 0, 0
    
    # Parse dates
    try:
        item_data['Date'] = pd.to_datetime(item_data['Last Updated'])
    except:
        return 0, 0, 0
    
    item_data = item_data.sort_values('Date')
    
    # Calculate supply changes (negative = items bought)
    if 'Supply' in item_data.columns:
        item_data['Supply'] = pd.to_numeric(item_data['Supply'], errors='coerce')
        item_data['supply_diff'] = item_data['Supply'].diff()
        item_data['buys'] = item_data['supply_diff'].apply(lambda x: -x if x < 0 else 0)
    else:
        return 0, 0, 0
    
    now = datetime.datetime.now()
    t_3h = now - datetime.timedelta(hours=3)
    t_24h = now - datetime.timedelta(hours=24)
    t_yesterday = (t_24h - datetime.timedelta(days=1)).replace(hour=0, minute=0)
    
    # Calculate buys in different time windows
    past_3h = item_data[item_data['Date'] >= t_3h]
    bought_3h = int(past_3h['buys'].sum()) if not past_3h.empty else 0
    
    past_24h = item_data[item_data['Date'] >= t_24h]
    bought_today = int(past_24h['buys'].sum()) if not past_24h.empty else 0
    
    past_yesterday = item_data[(item_data['Date'] >= t_yesterday) & (item_data['Date'] < t_24h.replace(hour=0, minute=0))]
    bought_yesterday = int(past_yesterday['buys'].sum()) if not past_yesterday.empty else 0
    
    return bought_3h, bought_today, bought_yesterday


def get_prediction_score(row, weights, comparison_col):
    """Calculate prediction confidence score with breakdown"""
    item_name = row['Item Name']
    current_price = float(str(row['Current Price']).replace('$', '')) if isinstance(row['Current Price'], str) else row['Current Price']
    current_supply = float(row['Supply']) if isinstance(row['Supply'], (int, float, str)) else 0
    
    # Get entry/comparison values
    try:
        entry_price = float(str(row[comparison_col]).replace('$', '')) if isinstance(row[comparison_col], str) else row[comparison_col]
    except:
        entry_price = current_price
    
    # Supply change (absorption metric)
    if current_supply > 0 and entry_price > 0:
        supply_pct = (current_supply - float(row.get('Supply', 0))) / max(1, float(row.get('Supply', 1)))
        abs_pts = np.clip(abs(supply_pct * 100) * 10, 0, 100)
    else:
        abs_pts = 0
    
    # Momentum (using approximate buys)
    bought_3h, bought_today, bought_yesterday = 0, 0, 0  # Can be enhanced with full history
    if bought_today > bought_yesterday and bought_today > 0:
        mom_pts = 100
    elif bought_3h > 0:
        mom_pts = 50
    else:
        mom_pts = 0
    
    # Divergence (price vs supply gap)
    if entry_price > 0:
        price_pct = (current_price - entry_price) / entry_price
        gap = supply_pct - price_pct if 'supply_pct' in locals() else 0
        div_pts = np.clip(gap * 500, 0, 100) if gap > 0 else 0
    else:
        div_pts = 0
    
    # Calculate total score
    total = (abs_pts * weights['abs']) + (mom_pts * weights['mom']) + (div_pts * weights['div'])
    total = round(total, 1)
    breakdown = f"A:{int(abs_pts)}|M:{int(mom_pts)}|D:{int(div_pts)}"
    
    # Determine signal
    if total >= 80:
        status = "🥇 PUMP READY"
        trend = "✅"
    elif total >= 50:
        status = "📈 STRENGTHENING"
        trend = "🔺"
    elif total < 15 and supply_pct < -0.05 if 'supply_pct' in locals() else False:
        status = "❌ DUMPING"
        trend = "⚠️"
    else:
        status = "⚖️ NEUTRAL"
        trend = "➖"
    
    return {
        'score': total,
        'signal': status,
        'trend': trend,
        'breakdown': breakdown,
        'buys_3h': bought_3h,
        'buys_today': bought_today
    }


def show_predictor_view(conn, comparison_type="Permanent"):
    """Show predictor with tabs for Permanent and Daily analysis"""
    
    # Load weights from session state
    weights = {
        'abs': st.session_state.get('w_abs', 0.4),
        'mom': st.session_state.get('w_mom', 0.3),
        'div': st.session_state.get('w_div', 0.3)
    }
    
    # Load monitored items
    try:
        items_df = conn.read(worksheet="Items", ttl=0)
    except:
        st.info("📭 No items to analyze. Add items in the Item Monitor first!")
        return
    
    if items_df.empty:
        st.info("📭 No items to analyze. Add items in the Item Monitor first!")
        return
    
    # Create market links
    items_df['Market'] = items_df['Item Name'].apply(
        lambda x: f"https://steamdt.com/cs2/{urllib.parse.quote(x)}"
    )
    
    # Determine comparison column
    if comparison_type == "Permanent":
        added_col = 'Added Date'
        price_col = 'Current Price'
        supply_col = 'Supply'
    else:  # Daily
        added_col = 'Last Updated'
        price_col = 'Current Price'
        supply_col = 'Supply'
    
    # Calculate prediction metrics
    pred_results = []
    for idx, row in items_df.iterrows():
        pred = get_prediction_score(row, weights, price_col)
        pred_results.append(pred)
    
    # Add predictions to dataframe
    pred_df = pd.DataFrame(pred_results)
    items_df['Score'] = pred_df['score']
    items_df['Signal'] = pred_df['signal']
    items_df['Trend'] = pred_df['trend']
    items_df['Breakdown'] = pred_df['breakdown']
    items_df['Buys_3H'] = pred_df['buys_3h']
    items_df['Buys_Today'] = pred_df['buys_today']
    
    # Sort by score
    items_df_sorted = items_df.sort_values('Score', ascending=False)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    if not items_df_sorted.empty:
        with col1:
            top_item = items_df_sorted.iloc[0]
            st.metric(
                "🥇 TOP PICK",
                top_item['Item Name'],
                f"Score: {top_item['Score']}"
            )
        
        with col2:
            st.metric(
                "📊 AVG Confidence",
                f"{items_df_sorted['Score'].mean():.1f}"
            )
        
        with col3:
            bottom_item = items_df_sorted.iloc[-1]
            st.metric(
                "⚠️ BOTTOM PICK",
                bottom_item['Item Name'],
                f"{bottom_item['Score']}",
                delta_color="inverse"
            )
    
    # Display table
    display_cols = ['Trend', 'Score', 'Signal', 'Breakdown', 'Item Name', 'Current Price', 'Supply', 'Buys_3H', 'Buys_Today', 'Market']
    available_cols = [col for col in display_cols if col in items_df_sorted.columns]
    
    col_config = {
        'Score': st.column_config.ProgressColumn('Confidence', min_value=0, max_value=100, format='%.0f'),
        'Buys_3H': st.column_config.NumberColumn('Bought 3H', format='%d ⚡'),
        'Buys_Today': st.column_config.NumberColumn('Bought Today', format='%d 🔥'),
        'Market': st.column_config.LinkColumn('SteamDT', display_text='Link')
    }
    
    st.dataframe(
        items_df_sorted[available_cols],
        use_container_width=True,
        column_config=col_config,
        hide_index=True
    )


def show_strategy_tuner():
    """Show strategy weight tuning interface"""
    st.header("🎯 Intelligence Strategy Tuner")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.w_abs = st.slider(
            "Absorption (Supply Choke)",
            0.0, 1.0,
            st.session_state.get('w_abs', 0.4),
            step=0.05,
            help="Weight for supply absorption metric"
        )
    
    with col2:
        st.session_state.w_mom = st.slider(
            "Momentum (Recent Sales)",
            0.0, 1.0,
            st.session_state.get('w_mom', 0.3),
            step=0.05,
            help="Weight for buying momentum"
        )
    
    with col3:
        st.session_state.w_div = st.slider(
            "Divergence (Price Lag)",
            0.0, 1.0,
            st.session_state.get('w_div', 0.3),
            step=0.05,
            help="Weight for price-supply divergence"
        )
    
    # Show normalized weights
    total = st.session_state.w_abs + st.session_state.w_mom + st.session_state.w_div
    if total > 0:
        st.info(f"**Normalized:** A:{st.session_state.w_abs/total:.1%} | M:{st.session_state.w_mom/total:.1%} | D:{st.session_state.w_div/total:.1%}")
    
    if st.button("♻️ Reset to Defaults"):
        st.session_state.w_abs = 0.4
        st.session_state.w_mom = 0.3
        st.session_state.w_div = 0.3
        st.rerun()
