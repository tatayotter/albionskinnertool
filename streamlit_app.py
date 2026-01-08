import streamlit as st
import requests
import pandas as pd

# --- CONSTANTS ---
HIDE_REQ = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
MOUNTS = {
    "Stag (T4)": 454, "Transport Ox (T5)": 1139, "Transport Ox (T8)": 3281,
    "Grizzly Bear (T7)": 2382, "Elite Winter Bear (T8)": 3485, "Mammoth (T8)": 23412
}
HIDE_WEIGHTS = {4: 0.3, 5: 0.5, 6: 0.8, 7: 1.2, 8: 2.0}

st.set_page_config(layout="wide", page_title="Albion Asia Pro")
st.title("📈 Martlock Arbitrage (Buy/Sell Orders)")

# --- SIDEBAR ---
st.sidebar.header("🚚 Logistics")
selected_mount = st.sidebar.selectbox("Select Mount", list(MOUNTS.keys()))
total_capacity = MOUNTS[selected_mount]
rrr_pct = st.sidebar.number_input("Total RRR %", min_value=15.0, value=15.0)

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def get_data():
    ids = ["T3_LEATHER"]
    for t in [4,5,6,7,8]:
        for e in [0,1,2,3,4]:
            suffix = f"@{e}" if e > 0 else ""
            ids.extend([f"T{t}_HIDE{suffix}", f"T{t}_LEATHER{suffix}"])
    url = f"https://east.albion-online-data.com/api/v2/stats/prices/{','.join(ids)}"
    try:
        return pd.DataFrame(requests.get(url).json())
    except:
        return pd.DataFrame()

if st.button("Calculate Best Trades"):
    df = get_data()
    if not df.empty:
        # CONVERT TO DICTIONARIES FOR ERROR-FREE LOOKUPS
        # Martlock prices for selling leather and buying bridge materials
        mtl_data = df[df['city'] == 'Martlock']
        mtl_buy_orders = mtl_data.set_index('item_id')['buy_price_max'].to_dict()
        mtl_sell_orders = mtl_data.set_index('item_id')['sell_price_min'].to_dict()
        
        # Best Hide Buy Orders (across all cities)
        best_hide_buy = df[df['item_id'].str.contains('HIDE')].groupby('item_id')['buy_price_max'].max().to_dict()

        results = []
        for t in [4,5,6,7,8]:
            for e in [0,1,2,3,4]:
                suffix = f"@{e}" if e > 0 else ""
                leather_id = f"T{t}_LEATHER{suffix}"
                hide_id = f"T{t}_HIDE{suffix}"
                ing_id = "T3_LEATHER" if t == 4 else f"T{t-1}_LEATHER{suffix}"

                # SAFE LOOKUPS
                h_price = best_hide_buy.get(hide_id, 0)
                ing_cost = mtl_sell_orders.get(ing_id, 0)
                l_price = mtl_sell_orders.get(leather_id, 0)

                if l_price > 0 and h_price > 0:
                    # Calculations
                    total_input = (h_price * HIDE_REQ[t]) + ing_cost
                    effective_cost = total_input * (1 - (rrr_pct/100))
                    # Sell order tax is ~6.5%
                    net_revenue = l_price * 0.935 
                    profit_per_bar = net_revenue - effective_cost
                    
                    # Logistics
                    hides_per_trip = int(total_capacity / HIDE_WEIGHTS[t])
                    total_trip_profit = (hides_per_trip / HIDE_REQ[t]) * profit_per_bar

                    results.append({
                        "Item": leather_id,
                        "Hide Buy Order": h_price,
                        "Leather Sell Order": l_price,
                        "Profit/Bar": round(profit_per_bar, 0),
                        "Total Trip Profit": round(total_trip_profit, 0)
                    })

        st.dataframe(pd.DataFrame(results).sort_values("Total Trip Profit", ascending=False), use_container_width=True)
