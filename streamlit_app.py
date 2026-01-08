import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONSTANTS & LOGISTICS ---
HIDE_REQ = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
MOUNTS = {
    "Stag (T4)": 454, "Transport Ox (T5)": 1139, "Transport Ox (T8)": 3281,
    "Grizzly Bear (T7)": 2382, "Elite Winter Bear (T8)": 3485, "Mammoth (T8)": 23412
}
# Official weights (Resource weight = 0.1 * 1.5^Tier)
HIDE_WEIGHTS = {4: 0.5, 5: 0.8, 6: 1.1, 7: 1.7, 8: 2.6}

st.set_page_config(layout="wide", page_title="Albion Asia: Martlock Tanner")
st.title("🏹 Martlock Tanner: Buy/Sell Order Arbitrage")

# --- 2. SIDEBAR CONFIGURATION ---
st.sidebar.header("🚚 Logistics & Settings")
selected_mount = st.sidebar.selectbox("Select Your Mount", list(MOUNTS.keys()))
total_capacity = MOUNTS[selected_mount]

rrr_pct = st.sidebar.number_input("Total RRR % (e.g., 15.2 or 36.7)", min_value=15.0, value=15.2, step=0.1)
market_tax = 0.065 # 4% Sales Tax + 2.5% Setup Fee

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=300)
def get_data():
    ids = ["T3_LEATHER"]
    for t in [4, 5, 6, 7, 8]:
        for e in [0, 1, 2, 3, 4]:
            suffix = f"@{e}" if e > 0 else ""
            ids.extend([f"T{t}_HIDE{suffix}", f"T{t}_LEATHER{suffix}"])
    
    url = f"https://east.albion-online-data.com/api/v2/stats/prices/{','.join(ids)}"
    try:
        response = requests.get(url)
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

# --- 4. CALCULATION LOGIC ---
if st.button("Calculate Profits"):
    df = get_data()
    
    if not df.empty:
        # Prep Martlock dictionary (For Leather & Ingredients)
        mtl_df = df[df['city'] == 'Martlock'].set_index('item_id')
        mtl_sell_prices = mtl_df['sell_price_min'].to_dict()
        mtl_dates = mtl_df['sell_price_min_date'].to_dict()
        
        # Prep Best Hide Buy Orders globally
        hide_df = df[df['item_id'].str.contains('HIDE')]
        best_hides = hide_df.groupby('item_id').agg({
            'buy_price_max': 'max',
            'city': 'first',
            'buy_price_max_date': 'first'
        }).to_dict('index')

        results = []
        for t in [4, 5, 6, 7, 8]:
            for e in [0, 1, 2, 3, 4]:
                suffix = f"@{e}" if e > 0 else ""
                leather_id = f"T{t}_LEATHER{suffix}"
                hide_id = f"T{t}_HIDE{suffix}"
                ing_id = "T3_LEATHER" if t == 4 else f"T{t-1}_LEATHER{suffix}"

                # Data Retrieval
                l_price = mtl_sell_prices.get(leather_id, 0)
                ing_cost = mtl_sell_prices.get(ing_id, 0)
                h_data = best_hides.get(hide_id, {})
                h_price = h_data.get('buy_price_max', 0)

                if l_price > 0 and h_price > 0:
                    # Calculations
                    total_raw_cost = (h_price * HIDE_REQ[t]) + ing_cost
                    effective_cost = total_raw_cost * (1 - (rrr_pct / 100))
                    net_revenue = l_price * (1 - market_tax)
                    profit_per_bar = net_revenue - effective_cost
                    
                    # Weight/Trip Logic
                    hides_per_trip = int(total_capacity / HIDE_WEIGHTS[t])
                    bars_per_trip = hides_per_trip // HIDE_REQ[t]
                    total_trip_profit = bars_per_trip * profit_per_bar

                    # Freshness
                    update_time = mtl_dates.get(leather_id, "Unknown")
                    
                    results.append({
                        "Item": leather_id,
                        "Buy Hides At": h_data.get('city', 'N/A'),
                        "Hide (Buy Order)": h_price,
                        "Leather (Sell Order)": l_price,
                        "Profit/Bar": round(profit_per_bar, 0),
                        "Total Trip Profit": round(total_trip_profit, 0),
                        "Last Updated": update_time
                    })

        # --- 5. DISPLAY RESULTS ---
        if results:
            final_df = pd.DataFrame(results)
            # Sort and Style
            st.dataframe(
                final_df.sort_values("Total Trip Profit", ascending=False).style.format({
                    "Profit/Bar": "{:,.0f} Silver",
                    "Total Trip Profit": "{:,.0f} Silver"
                }), 
                use_container_width=True
            )
        else:
            st.warning("No complete market data found. Try opening the Market Board in Martlock with your Data Client running.")
    else:
        st.error("The Albion Data Project returned no data. Check if the Asia server is online.")
