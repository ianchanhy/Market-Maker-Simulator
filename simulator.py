import streamlit as st
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots


st.set_page_config(layout="wide", page_title="Market Maker Simulator")
st.title("Market Maker Simulator")
st.write("by Ian Chan H.Y.")


st.sidebar.title("Simulation Parameters")

# Initial Setup
st.sidebar.header("Initial Setup")
INITIAL_FAIR_VALUE = st.sidebar.number_input("Initial Fair Value ($)", value=100.0)
INITIAL_CASH = st.sidebar.number_input("Initial Cash ($)", value=10000.0)
RUN_SPEED = st.sidebar.select_slider("Run Speed (sec)", options=[0, 0.1, 0.25, 0.5, 1], value=0.1)
SIMULATION_HORIZON_T = st.sidebar.number_input("Simulation Horizon (T steps)", value=1000, min_value=100)


# Market Parameters
st.sidebar.header("Market Parameters")
MEAN_VOLATILITY = st.sidebar.slider("Mean Volatility (Target)", 0.01, 0.5, 0.1, 0.01)
VOL_REVERSION_SPEED = st.sidebar.slider("Volatility Reversion Speed", 0.0, 1.0, 0.1, 0.01)
VOL_VOLATILITY = st.sidebar.slider("Volatility of Volatility", 0.0, 0.1, 0.005, 0.001)

# Taker Parameters
st.sidebar.header("Taker Parameters")
TAKER_BUY_PROB = st.sidebar.slider("Base Taker Buy Prob", 0.0, 1.0, 0.5, 0.01)
TAKER_SELL_PROB = st.sidebar.slider("Base Taker Sell Prob", 0.0, 1.0, 0.5, 0.01)
TAKER_INTENSITY_K = st.sidebar.slider("Taker Intensity (k)", 0.1, 50.0, 10.0, 0.1)


# Market Maker Parameters
st.sidebar.header("Your (AS Model) Parameters")
INVENTORY_RISK_AVERSION = st.sidebar.slider("Inventory Risk Aversion (gamma)", 0.001, 0.1, 0.01, 0.001)
MAX_INVENTORY = st.sidebar.slider("Max Inventory (Short or Long)", 1, 100, 20)


def log_history():
    """Logs the current state for the charts."""
    st.session_state.history.append({
        "Step": st.session_state.step,
        "P&L": st.session_state.mtm_pnl,
        "Inventory": st.session_state.inventory,
        "Fair Value": st.session_state.fair_value,
        "Bid": st.session_state.our_bid,
        "Ask": st.session_state.our_ask,
        "Volatility": st.session_state.current_volatility,
        "Spread": st.session_state.current_spread
    })


def calculate_quotes():
    """Calculate "smart" quotes using the Avellaneda-Stoikov model."""
    
    # Get AS model parameters
    gamma = INVENTORY_RISK_AVERSION
    k = TAKER_INTENSITY_K
    vol = st.session_state.current_volatility
    inv = st.session_state.inventory
    fair_value = st.session_state.fair_value
    
    # Calculate time remaining
    time_left = max(0.001, (SIMULATION_HORIZON_T - st.session_state.step) / SIMULATION_HORIZON_T)

    # Calculate Indifference Price
    indifference_price = fair_value - (inv * gamma * (vol**2) * time_left)
    
    # Calculate Optimal Spread
    vol_spread_component = gamma * (vol**2) * time_left
    adverse_selection_component = (2 / gamma) * np.log(1 + (gamma / k))
    
    optimal_spread = vol_spread_component + adverse_selection_component
    
    st.session_state.current_spread = optimal_spread
    
    # Set Final Quotes
    st.session_state.our_bid = indifference_price - (optimal_spread / 2)
    st.session_state.our_ask = indifference_price + (optimal_spread / 2)

    # Pull quotes at max inventory
    if st.session_state.inventory >= MAX_INVENTORY:
        st.session_state.our_bid = np.nan  
    if st.session_state.inventory <= -MAX_INVENTORY:
        st.session_state.our_ask = np.nan 
    
    # Handle "end of day"
    if time_left <= 0.001:
        st.session_state.our_bid = np.nan
        st.session_state.our_ask = np.nan
        st.session_state.current_spread = 0
        

def initialize_state():
    """Sets all session state variables to their initial values."""
    st.session_state.fair_value = INITIAL_FAIR_VALUE
    st.session_state.current_volatility = MEAN_VOLATILITY  
    st.session_state.cash = INITIAL_CASH
    st.session_state.inventory = 0
    st.session_state.mtm_pnl = 0.0
    
    st.session_state.trade_log = []
    st.session_state.history = [] 
    
    st.session_state.step = 0 
    
    st.session_state.initialized = True
    st.session_state.running = False 
    
    calculate_quotes() 
    log_history() 


if 'initialized' not in st.session_state:
    initialize_state()

if st.sidebar.button("RESET SIMULATION"):
    initialize_state()
    st.rerun() 


def update_volatility():
    """Update the market's volatility using a mean-reverting process."""
    current_vol = st.session_state.current_volatility
    reversion = VOL_REVERSION_SPEED * (MEAN_VOLATILITY - current_vol)
    noise = np.random.normal(0, VOL_VOLATILITY)
    vol_move = reversion + noise
    st.session_state.current_volatility = max(0.01, current_vol + vol_move)

def update_fair_value():
    """Simulate the Market's "Fair Value" as a random walk."""
    move = np.random.normal(0, st.session_state.current_volatility)
    st.session_state.fair_value += move

def calculate_pnl():
    """Calculate our Mark-to-Market (MTM) P&L."""
    unrealized_pnl = st.session_state.inventory * st.session_state.fair_value
    realized_pnl = st.session_state.cash - INITIAL_CASH
    st.session_state.mtm_pnl = realized_pnl + unrealized_pnl
    
def log_trade(trade_type, quantity, price):
    """Helper function to record trades in the log."""
    st.session_state.trade_log.append({
        "Step": st.session_state.step,
        "Type": trade_type,
        "Quantity": quantity,
        "Price": f"${price:.2f}",
        "Inventory": st.session_state.inventory,
        "Cash": f"${st.session_state.cash:.2f}"
    })


def simulate_taker_trades():
    """Simulate "smarter" takers who are price-sensitive."""
    fv = st.session_state.fair_value
    k = TAKER_INTENSITY_K
    
    # Taker Buy Logic
    if pd.notna(st.session_state.our_ask):
        distance_from_fv = st.session_state.our_ask - fv
        buy_prob = TAKER_BUY_PROB * np.exp(-k * distance_from_fv)
        buy_prob = np.clip(buy_prob, 0, 1)

        if np.random.rand() < buy_prob:
            st.session_state.inventory -= 1
            st.session_state.cash += st.session_state.our_ask
            log_trade("Taker Buy (Bot Sell)", 1, st.session_state.our_ask)

    # Taker Sell Logic
    if pd.notna(st.session_state.our_bid):
        distance_from_fv = fv - st.session_state.our_bid
        sell_prob = TAKER_SELL_PROB * np.exp(-k * distance_from_fv)
        sell_prob = np.clip(sell_prob, 0, 1)
        
        if np.random.rand() < sell_prob:
            st.session_state.inventory += 1
            st.session_state.cash -= st.session_state.our_bid
            log_trade("Taker Sell (Bot Buy)", 1, st.session_state.our_bid)


def run_simulation_step():
    """Combines all steps into one simulation "tick"."""
    st.session_state.step += 1
    update_volatility()
    update_fair_value()
    calculate_quotes()      
    simulate_taker_trades() 
    calculate_pnl()
    log_history()

# --- Main App Layout ---

col1, col2 = st.columns([1, 4])
if col1.button("Run 1 Step"):
    run_simulation_step()
    st.rerun()

col2.checkbox("Auto-Run Simulation", key="running")


# Live Dashboard
st.subheader("Live Dashboard")
col1, col2, col3, col4, col5, col6 = st.columns(6)

bid_display = f"{st.session_state.our_bid:.2f}" if pd.notna(st.session_state.our_bid) else "N/A"
ask_display = f"{st.session_state.our_ask:.2f}" if pd.notna(st.session_state.our_ask) else "N/A"

col1.metric("MTM P&L ($)", f"{st.session_state.mtm_pnl:.2f}")
col2.metric("Inventory", f"{st.session_state.inventory}")
col3.metric("Fair Value ($)", f"{st.session_state.fair_value:.2f}")
col4.metric("Market Vol", f"{st.session_state.current_volatility:.3f}") 
col5.metric("Our Bid ($)", bid_display) 
col6.metric("Our Ask ($)", ask_display) 


# Manual Trading
st.subheader("Manual Trading")

bid_label = f"${st.session_state.our_bid:.2f}" if pd.notna(st.session_state.our_bid) else "N/A"
ask_label = f"${st.session_state.our_ask:.2f}" if pd.notna(st.session_state.our_ask) else "N/A"

col1, col2 = st.columns(2)
if col1.button(f"BUY from Bot (Lift Ask: {ask_label})"): 
    if pd.notna(st.session_state.our_ask): 
        st.session_state.inventory -= 1 
        st.session_state.cash += st.session_state.our_ask
        log_trade("User Buy (Bot Sell)", 1, st.session_state.our_ask)
        calculate_pnl()
        st.rerun()
    else:
        st.warning("Bot is not quoting an ask right now (max short).")

if col2.button(f"SELL to Bot (Hit Bid: {bid_label})"): 
    if pd.notna(st.session_state.our_bid): 
        st.session_state.inventory += 1
        st.session_state.cash -= st.session_state.our_bid
        log_trade("User Sell (Bot Buy)", 1, st.session_state.our_bid)
        calculate_pnl()
        st.rerun()
    else:
        st.warning("Bot is not quoting a bid right now (max long).")


# Simulation History Charts
st.subheader("Simulation History")
chart_placeholder = st.empty()

def draw_charts():
    """Draws the main P&L, Price, and Inventory charts."""
    if len(st.session_state.history) > 0:

        hist_df = pd.DataFrame(st.session_state.history).set_index("Step")
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                            subplot_titles=("P&L", "Market Prices", "Inventory", "Volatility & Quoted Spread"),
                            vertical_spacing=0.05,
                            specs=[[{}], [{}], [{}], [{"secondary_y": True}]]) 

        # P&L Plot
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df["P&L"], name="MTM P&L", line=dict(color='blue')), row=1, col=1)

        # Prices Plot
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df["Fair Value"], name="Fair Value", line=dict(color='black', dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df["Bid"], name="Our Bid", line=dict(color='green', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df["Ask"], name="Our Ask", line=dict(color='red', width=1)), row=2, col=1)

        # Inventory Plot
        fig.add_trace(
            go.Scatter(x=hist_df.index, y=hist_df["Inventory"], name="Inventory", line=dict(color='purple'), fill='tozeroy'), 
            row=3, col=1
        )
        
        # Volatility & Spread Plot
        fig.add_trace(
            go.Scatter(x=hist_df.index, y=hist_df["Volatility"], name="Market Vol", line=dict(color='orange')), 
            row=4, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=hist_df.index, y=hist_df["Spread"], name="Quoted Spread ($)", line=dict(color='cyan', dash='dash')), 
            row=4, col=1, secondary_y=True
        )
        
        fig.update_layout(height=800, showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        
        # Y-Axis Titles
        fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
        fig.update_yaxes(title_text="Price ($)", row=2, col=1)
        fig.update_yaxes(title_text="Units", row=3, col=1)
        fig.update_yaxes(title_text="Volatility", row=4, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Spread ($)", row=4, col=1, secondary_y=True)
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)


draw_charts()


# Trade Log
st.subheader("Trade Log")
if len(st.session_state.trade_log) > 0:
    log_df = pd.DataFrame(st.session_state.trade_log).sort_index(ascending=False)
    st.dataframe(log_df.head(20), use_container_width=True, height=200)
else:
    st.info("No trades have occurred yet.")


# Auto-run loop
if st.session_state.get("running", False):
    if st.session_state.step >= SIMULATION_HORIZON_T:
        st.session_state.running = False
        st.warning("Simulation Horizon T reached. Market is closed. RESET to run again.")
    else:
        run_simulation_step()
        draw_charts()
        time.sleep(RUN_SPEED)
        st.rerun()