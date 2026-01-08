import streamlit as st
import requests
import pandas as pd

# --- DATA CONSTANTS ---
HIDE_REQ = {4: 2, 5: 3, 6: 4, 7: 5, 8: 5}
# Weight in KG (Base weights for popular transport mounts)
MOUNTS = {
    "Stag (T4)": 454,
    "Transport Ox (T5)": 1139,
    "Transport Ox (T8)": 3281,
    "Grizzly Bear (T7)": 2382,
    "Elite Winter Bear (T8)": 3485,
    "Mammoth (T8)": 23412
}
# Item weights in KG
HIDE_WEIGHTS = {4: 0.3, 5: 0.5, 6: 0.8, 7: 1.2, 8: 2.0}

st.set_page_config(layout="wide", page_title="Albion Asia: Arbitrage Pro")
st.title("📈 Martlock Leather: Buy/Sell Order Arbitrage")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("🚚 Logistics & Stats")
selected_mount = st.sidebar.selectbox("Select Your Mount", list(MOUNTS.keys()))
bag_bonus = st.sidebar.number_input("Bag/Passive Weight Bonus (KG)", value=0)
total_capacity = MOUNTS[selected_mount] + bag_bonus

st.sidebar.divider()
rrr_pct = st.sidebar.number_input("Total RRR % (e.g., 15.2 or 36.7)", min_value=15.0, value=15.0)
market_tax = 0.065  # 4% Tax + 2.5% Setup for Sell Orders

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def get_data():
    ids = ["T3_LEATHER"]
    for t in [4,5,6,7,8]:
        for e in [0,1,2,3,4]:
            suffix = f"@{e}" if e > 0 else ""
            ids.extend([f"T{t}_HIDE{suffix}", f"T{t}_LEATHER{suffix}"])
    url = f"https://east.albion-online-data.com/api/v2/stats/prices/{','.join(ids)}"
    return pd.DataFrame(requests.get(url).json())

if st.button("Calculate Best Trades"):
    df = get_data()
    if not df.empty:
        # We use Sell Orders to sell Leather (sell_price_min is the current lowest listing)
        # We use Buy Orders to buy Hides (buy_price_max is the highest existing bid)
        mtl_prices = df[df['city'] == 'Martlock'].set_index('item_id')
        
        results = []
        for t in [4,5,6,7,8]:
            for e in [0,1,2,3,4]:
                suffix = f"@{e}" if e > 0 else ""
                leather_id = f"T{t}_LEATHER{suffix}"
                hide_id = f"T{t}_HIDE{suffix}"
                
                # Ingredient logic
                ing_id = "T3_LEATHER" if t == 4 else f"T{t-1}_LEATHER{suffix}"
                
                # Prices
                # 1. Buying Hides via Buy Order (highest existing bid + 1 silver)
                hide_data = df[df['item_id'] == hide_id].sort_values('buy_price_max', ascending=False)
                if hide_data.empty: continue
                
                h_price = hide_data.iloc[0]['buy_price_max']
                h_city = hide_data.iloc[0]['city']
                
                # 2. Buying Ingredients in Martlock (Instant buy to save time)
                ing_cost = mtl_prices.loc[ing_id]['sell_price_min'] if ing_id in mtl_prices.index else 0
                
                # 3. Selling Leather in Martlock (Sell Order)
                l_price = mtl_prices.loc[leather_id]['sell_price_min'] if leather_id in mtl_prices.index else 0

                if l_price > 0 and h_price > 0:
                    # Calculations
                    total_input = (h_price * HIDE_REQ[t]) + ing_cost
                    effective_cost = total_input * (1 - (rrr_pct/100))
                    net_revenue = l_price * (1 - market_tax)
                    profit_per_bar = net_revenue - effective_cost
                    
                    # Logistics
                    hides_per_trip = int(total_capacity / HIDE_WEIGHTS[t])
                    total_trip_profit = hides_per_trip * (profit_per_bar / HIDE_REQ[t])

                    results.append({
                        "Item": leather_id,
                        "Buy Hides At": h_city,
                        "Hide Price": h_price,
                        "Leather Price": l_price,
                        "Profit/Bar": round(profit_per_bar, 0),
                        "Bars/Trip": hides_per_trip // HIDE_REQ[t],
                        "Total Trip Profit": round(total_trip_profit, 0)
                    })

        res_df = pd.DataFrame(results)
        
        # Display Best Options
        st.subheader(f"Top Profits for {selected_mount}")
        st.dataframe(
            res_df.sort_values("Total Trip Profit", ascending=False)
            .style.format({"Total Trip Profit": "{:,.0f} Silver", "Profit/Bar": "{:,.0f}"}),
            use_container_width=True
        )

st.warning("⚠️ **Reminder:** Ensure the data is fresh. High profits on old data are usually price spikes that have already been filled.")
