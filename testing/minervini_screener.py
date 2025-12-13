import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import datetime
import numpy as np

# ==========================================
# CONFIGURATION
# ==========================================
# List of Indian Stocks to Screen (Example: Nifty Top Stocks)
# In a real scenario, you can load a CSV of all 500 NSE tickers
TICKER_LIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "BAJFINANCE.NS",
    "MARUTI.NS", "ADANIENT.NS", "SUNPHARMA.NS", "TITAN.NS"
]

INDEX_TICKER = "^NSEI"  # Nifty 50 Index for RS Calculation
LOOKBACK_YEARS = 2      # Fetch enough data for 200 DMA

def fetch_data(ticker):
    """Fetches data from Yahoo Finance."""
    start_date = datetime.datetime.now() - datetime.timedelta(days=LOOKBACK_YEARS*365)
    df = yf.download(ticker, start=start_date, progress=False)
    
    # Handle MultiIndex columns (yfinance update)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df

def calculate_minervini_metrics(df):
    """Calculates Moving Averages and RS metrics."""
    if len(df) < 200:
        return None

    # Moving Averages
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_150'] = ta.sma(df['Close'], length=150)
    df['SMA_200'] = ta.sma(df['Close'], length=200)

    # 52 Week High/Low
    df['52_Week_Low'] = df['Close'].rolling(window=260).min()
    df['52_Week_High'] = df['Close'].rolling(window=260).max()

    # Slope of 200 SMA (Check if rising)
    # We check if current SMA_200 is greater than SMA_200 1 month ago (approx 20 trading days)
    df['SMA_200_Trending'] = df['SMA_200'] > df['SMA_200'].shift(20)

    return df

def calculate_relative_strength(stocks_df, index_df):
    """
    Calculates an RS Rating (0-99) roughly based on IBD methodology.
    Weighted Performance: 40% (3m) + 20% (6m) + 20% (9m) + 20% (12m)
    """
    rs_scores = {}
    
    # Helper for ROC
    def get_roc(df, months):
        days = months * 21
        if len(df) < days: return 0
        try:
            current = df['Close'].iloc[-1]
            past = df['Close'].iloc[-days]
            if pd.isna(current) or pd.isna(past) or past == 0: return 0 # Handle NaNs
            return ((current - past) / past) * 100
        except: return 0

    for ticker, df in stocks_df.items():
        score = (0.4 * get_roc(df, 3)) + (0.2 * get_roc(df, 6)) + \
                (0.2 * get_roc(df, 9)) + (0.2 * get_roc(df, 12))
        rs_scores[ticker] = score

    # Convert to DataFrame to rank
    rs_df = pd.DataFrame.from_dict(rs_scores, orient='index', columns=['Raw_Score'])
    rs_df['RS_Rating'] = rs_df['Raw_Score'].rank(pct=True) * 99
    return rs_df

def check_trend_template(df, current_price, rs_rating):
    """
    Checks if the stock meets Mark Minervini's 8 Trend Template criteria.
    """
    if df is None or len(df) < 200: return False

    curr = df.iloc[-1]
    
    # 1. Price > 150 & 200 SMA
    c1 = current_price > curr['SMA_150'] and current_price > curr['SMA_200']
    
    # 2. 150 SMA > 200 SMA
    c2 = curr['SMA_150'] > curr['SMA_200']
    
    # 3. 200 SMA Trending Up (for at least 1 month)
    c3 = curr['SMA_200_Trending']
    
    # 4. 50 SMA > 150 & 200 SMA
    c4 = curr['SMA_50'] > curr['SMA_150'] and curr['SMA_50'] > curr['SMA_200']
    
    # 5. Price > 50 SMA
    c5 = current_price > curr['SMA_50']
    
    # 6. Price > 30% above 52-Week Low
    c6 = current_price >= (1.30 * curr['52_Week_Low'])
    
    # 7. Price within 25% of 52-Week High
    c7 = current_price >= (0.75 * curr['52_Week_High'])
    
    # 8. RS Rating > 70 (We use >= 70)
    c8 = rs_rating >= 70

    return c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8

def analyze_volatility_contraction(df):
    """
    Simple VCP detection: Checks if recent volatility is lower than historical.
    """
    # Standard Deviation of last 10 days vs last 60 days
    vol_10 = df['Close'].rolling(10).std().iloc[-1]
    vol_60 = df['Close'].rolling(60).std().iloc[-1]
    
    contraction = False
    if vol_10 < (vol_60 * 0.5): # Volatility is half of what it was
        contraction = True
        
    return contraction

def plot_minervini_chart(ticker, df):
    """Generates a professional candle chart with SMAs."""
    # Slice last 1 year for visibility
    plot_df = df.iloc[-250:]
    
    apds = [
        mpf.make_addplot(plot_df['SMA_50'], color='blue', width=1.5, panel=0),
        mpf.make_addplot(plot_df['SMA_150'], color='orange', width=1.5, panel=0),
        mpf.make_addplot(plot_df['SMA_200'], color='black', width=2.0, panel=0),
    ]
    
    mpf.plot(
        plot_df, 
        type='candle', 
        style='yahoo', 
        volume=True, 
        addplot=apds,
        title=f'\nMinervini Setup: {ticker}',
        ylabel='Price (INR)',
        ylabel_lower='Volume'
    )
    print(f"Chart generated for {ticker}")

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("Fetching data and calculating Relative Strength...")
    
    stock_data = {}
    
    # 1. Fetch Data
    for ticker in TICKER_LIST:
        try:
            df = fetch_data(ticker)
            if df is not None and not df.empty:
                stock_data[ticker] = calculate_minervini_metrics(df)
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

    # 2. Calculate RS Ratings
    rs_df = calculate_relative_strength(stock_data, None) # Index comparison omitted for speed in this demo
    
    passed_stocks = []
    
    print("\n--- Screening Results ---")
    for ticker, df in stock_data.items():
        if df is None: continue
        
        current_price = df['Close'].iloc[-1]
        rs = rs_df.loc[ticker, 'RS_Rating']
        
        if check_trend_template(df, current_price, rs):
            vcp = analyze_volatility_contraction(df)
            vcp_status = "POSSIBLE VCP (Tight)" if vcp else "Normal Volatility"
            
            # Entry/Exit Logic
            pivot_point = df['High'].iloc[-20:].max() # Simple 20-day high breakout
            stop_loss = current_price * 0.92 # 8% Stop Loss
            
            print(f"✅ PASS: {ticker} | Price: {current_price:.2f} | RS: {int(rs)} | Status: {vcp_status}")
            print(f"   -> Suggest Entry (Breakout): {pivot_point:.2f}")
            print(f"   -> Stop Loss: {stop_loss:.2f}")
            
            passed_stocks.append(ticker)
            
            # Plot the first passed stock as example
            plot_minervini_chart(ticker, df)
    
    if not passed_stocks:
        print("No stocks met the strict Minervini Trend Template criteria today.")

if __name__ == "__main__":
    main()