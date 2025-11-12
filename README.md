# **Interactive Market Maker Simulator**
This is a project I built to learn and demonstrate the core fundamentals of quantitative market making.

It's an interactive dashboard (built with Streamlit) that simulates a market maker's "brain" trying to quote prices, manage risk, and make a profit in a dynamic, "live" market. The "brain" itself is a complete implementation of the  2008 Avellaneda-Stoikov academic model, which solves for the optimal prices to quote.


## **How to Run**
1. Clone this repository:git clone https://github.com/ianchanhy/market-maker-simulator.git

2. Move into the folder:cd market-maker-simulator

3. Install the required libraries:pip install -r requirements.txt

4. Run the Streamlit app:streamlit run simulator.py

## **Core Features**
**Interactive Dashboard:** Uses Streamlit for a live dashboard with sliders and real-time charts.

**Dynamic Market:** The "fair value" (true price) of the asset follows a random walk, but its "craziness" (volatility) is also dynamic and follows a mean-reverting process.

**Adverse Selection:** The "takers" (other traders) are "smart" and price-sensitive. They are more likely to trade with you when your price is "wrong," simulating the core risk of adverse selection.

**The "Brain" (Avellaneda-Stoikov):** The bot isn't just using simple rules. It's using a formal academic model to calculate its Indifference Price (a smarter, skewed mid-price) and its Optimal Spread based on:

- Its own inventory risk

- Market volatility

- Taker "smartness"

- A ticking "end-of-day" clock

## **Understanding the Simulator: A Guide to the Parameters**
The simulation is a "world" with three main players: The Market, The Takers (your opponents), and Your Bot (your "brain").

**The Market's Parameters (The "World")**
These sliders control the "physics" of the market itself.

- MEAN_VOLATILITY: The "normal" or average level of craziness.

- VOL_REVERSION_SPEED: How fast the market "calms down" after a spike of craziness (or "heats up" after a calm period).

- VOL_VOLATILITY: The "craziness of the craziness." A high value here means the market's volatility itself is unpredictable.

**The Takers' Parameters (The "Opponents")**
These sliders control the "personality" of the other traders in the market.

- BASE_TAKER_..._PROB: The "base urgency" of the market. A high value means lots of people want to trade, regardless of price.

- TAKER_INTENSITY (k): This is the most important parameter for risk. It controls the "smartness" or "pickiness" of the takers.

   - High k (e.g., 50) = "Sharks": These takers are extremely price-sensitive. They have a np.exp(-50 * ...) function in their brain, meaning they will only trade with you if your price is a mistake. This is high adverse selection risk.

  - Low k (e.g., 0.1) = "Dumb Takers": These takers are not price-sensitive. They'll happily trade at almost any price you quote. This is low adverse selection risk.

**Your Bot's (AS Model) Parameters (Your "Brain")**
These are the inputs you give your "brain" to define its strategy and personality.

- SIMULATION_HORIZON_T: The "end of the day," in steps. The bot knows this. The time_left is a critical multiplier in its formulas. As time approaches zero, the bot will panic to get its inventory to zero.

- INVENTORY_RISK_AVERSION (gamma): This is your bot's "fear" or "risk" setting.

  - High gamma = "Scared": The bot hates holding inventory. It will aggressively skew its prices just to get rid of a small position and get back to flat (zero).

  - Low gamma = "Brave": The bot doesn't mind holding large positions. It will skew less and try to capture more trades.

- MAX_INVENTORY: A simple "circuit breaker." If the bot's inventory gets this high, it will stop quoting on one side (e.g., stop bidding if its inventory is too high).
