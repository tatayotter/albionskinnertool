import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

# --- 1. CONSTANTS & LOGISTICS ---
HIDE_REQ = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
MOUNTS = {
    "Stag (T4)": 454, "Transport Ox (T5)": 1139, "Transport Ox (T8)": 3281,
    "Grizzly Bear (T7)": 2382, "Elite Winter Bear (T8)": 3485, "Mammoth (T8)": 23412
}
HIDE_WEIGHTS = {4: 0.5, 5: 0.8, 6: 1.1, 7: 1.7, 8: 2.6}

st.set_page_config(layout="wide", page_title="Albion Asia: Martlock Tanner")
st.title("🏹 Martlock Tanner: Historical & Live Data")

# --- 2. SIDEBAR ---
st.sidebar.header("🚚 Logistics & Settings")
selected_mount = st.sidebar.selectbox("Select Your Mount", list(MOUNTS.keys()))
total_capacity = MOUNTS[selected_mount]
rrr_pct = st.sidebar.number_input("Total RRR %", min_value=15.0, value=15.2, step=0.1)
market_tax = 0.065 

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=60)
def get_data():
    ids = ["T3_LEATHER"]
    for t in [4, 5, 6, 7, 8]:
        for e in [0, 1, 2, 3, 4]:
            suffix = f"@{e}" if e > 0 else ""
            ids.extend([f"T{t}_HIDE{suffix}", f"T{t}_LEATHER{suffix}"])
    
    # Target ASIA Server
    url = f"https://east.albion-online-data.com/api/v2/stats/prices/{','.join(ids)}"
    try:
        response = requests.get(url)
        return pd.DataFrame(response.json())
    except:
        return pd.DataFrame()

# --- 4. FORMATTING HELPER ---
def color_age(val):
    try:
        dt = pd.to_datetime(val)
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds() / 3600
        if diff < 1: return 'background-color: #90ee90; color: black' # Fresh (<1hr)
        if diff < 24: return 'background-color: #ffff99; color: black' # Recent (<24hr)
        return 'background-color: #ffcccb; color: black' # Old (>24hr)
    except:
        return ''

# --- 5. MAIN LOGIC ---
if st.button("Calculate Profits"):
    df = get_data()
    
    if not df.empty:
        mtl_df = df[df['city'] == 'Martlock'].set_index('item_id')
        mtl_sell_prices = mtl_df['sell_price_min'].to_dict()
        mtl_dates = mtl_df['sell_price_min_date'].to_dict()
        
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

                l_price = mtl_sell_prices.get(leather_id, 0)
                ing_cost = mtl_sell_prices.get(ing_id, 0)
                h_data = best_hides.get(hide_id, {})
                h_price = h_data.get('buy_price_max', 0)

                # We now allow l_price or h_price to be shown even if old
                # as long as they aren't zero.
                if l_price > 0 and h_price > 0:
                    total_raw_cost = (h_price * HIDE_REQ[t]) + ing_cost
                    effective_cost = total_raw_cost * (1 - (rrr_pct / 100))
                    net_revenue = l_price * (1 - market_tax)
                    profit_per_bar = net_revenue - effective_cost
                    
                    hides_per_trip = int(total_capacity / HIDE_WEIGHTS[t])
                    total_trip_profit = (hides_per_trip // HIDE_REQ[t]) * profit_per_bar
                    
                    results.append({
                        "Item": leather_id,
                        "Hide City": h_data.get('city', 'N/A'),
                        "Hide BuyOrder": h_price,
                        "Leather SellOrder": l_price,
                        "Profit/Bar": round(profit_per_bar, 0),
                        "Trip Profit": round(total_trip_profit, 0),
                        "Last Updated": mtl_dates.get(leather_id, "N/A")
                    })

        if results:
            final_df = pd.DataFrame(results)
            styled_df = final_df.sort_values("Trip Profit", ascending=False).style.applymap(color_age, subset=['Last Updated'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No price records found for these items in the database yet.")
    else:
        st.error("API connection failed.")
