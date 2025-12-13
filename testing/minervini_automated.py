import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import datetime
import os
import numpy as np

# ==========================================
# CONFIGURATION
# ==========================================
# Comprehensive List of Stocks (Example: Mix of Nifty 50 & Midcaps)
TICKER_LIST = [
    "TCS.NS", "INFY.NS", "HDFCBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "ADANIENT.NS", "TITAN.NS", "TRENT.NS", "DIVISLAB.NS", "LALPATHLAB.NS",
    "BAJAJHFL.NS", "TATAELXSI.NS", "HDFCGOLD.NS", "NESTLEIND.NS", "GMMPFAUDLR.NS",
    "EICHERMOT.NS", "M&M.NS", "CLEAN.NS"
]

# Create directories if they don't exist
CHARTS_DIR = "minervini_charts"
REPORTS_DIR = "minervini_reports"
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

LOOKBACK_YEARS = 2

def fetch_data(ticker):
    """Fetches data from Yahoo Finance."""
    start_date = datetime.datetime.now() - datetime.timedelta(days=LOOKBACK_YEARS*365)
    # auto_adjust=True fixes OHLC for splits/dividends
    df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty:
        return None
        
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
    df['SMA_200_Trending'] = df['SMA_200'] > df['SMA_200'].shift(20)

    return df

def calculate_relative_strength(stocks_df):
    """
    Calculates an RS Rating (0-99) for the provided list of stocks against each other.
    """
    rs_scores = {}
    
    def get_roc(df, months):
        days = int(months * 21)
        if len(df) < days: return 0
        try:
            current = df['Close'].iloc[-1]
            past = df['Close'].iloc[-days]
            return ((current - past) / past) * 100
        except: return 0

    for ticker, df in stocks_df.items():
        if df is None: continue
        score = (0.4 * get_roc(df, 3)) + (0.2 * get_roc(df, 6)) + \
                (0.2 * get_roc(df, 9)) + (0.2 * get_roc(df, 12))
        rs_scores[ticker] = score

    if not rs_scores:
        return pd.DataFrame()

    rs_df = pd.DataFrame.from_dict(rs_scores, orient='index', columns=['Raw_Score'])
    rs_df['RS_Rating'] = rs_df['Raw_Score'].rank(pct=True) * 99
    return rs_df

def check_trend_template(df, current_price, rs_rating):
    """Minervini's 8 Trend Template Criteria"""
    if df is None or len(df) < 200: return False

    curr = df.iloc[-1]
    
    c1 = current_price > curr['SMA_150'] and current_price > curr['SMA_200']
    c2 = curr['SMA_150'] > curr['SMA_200']
    c3 = curr['SMA_200_Trending']
    c4 = curr['SMA_50'] > curr['SMA_150'] and curr['SMA_50'] > curr['SMA_200']
    c5 = current_price > curr['SMA_50']
    c6 = current_price >= (1.30 * curr['52_Week_Low'])
    c7 = current_price >= (0.75 * curr['52_Week_High'])
    c8 = rs_rating >= 70

    return c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8

def analyze_volatility_contraction(df):
    """Detects if volatility is drying up (VCP characteristic)."""
    vol_10 = df['Close'].rolling(10).std().iloc[-1]
    vol_60 = df['Close'].rolling(60).std().iloc[-1]
    return vol_10 < (vol_60 * 0.5)

def save_minervini_chart(ticker, df, today_str):
    """Saves the chart to the disk instead of showing it."""
    plot_df = df.iloc[-200:] # Last 200 days for better view
    
    apds = [
        mpf.make_addplot(plot_df['SMA_50'], color='blue', width=1.5, panel=0),
        mpf.make_addplot(plot_df['SMA_150'], color='orange', width=1.5, panel=0),
        mpf.make_addplot(plot_df['SMA_200'], color='black', width=2.0, panel=0),
    ]
    
    filename = f"{CHARTS_DIR}/{ticker}_{today_str}.png"
    
    mpf.plot(
        plot_df, 
        type='candle', 
        style='yahoo', 
        volume=True, 
        addplot=apds,
        title=f'\nMinervini Setup: {ticker} ({today_str})',
        ylabel='Price (INR)',
        ylabel_lower='Volume',
        savefig=filename  # This saves the file!
    )
    return filename

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("--- Starting Minervini Screener for Indian Market ---")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    stock_data = {}
    
    # 1. Fetch Data
    print("Fetching data (this may take a moment)...")
    for ticker in TICKER_LIST:
        try:
            df = fetch_data(ticker)
            if df is not None:
                stock_data[ticker] = calculate_minervini_metrics(df)
        except Exception as e:
            print(f"Failed to fetch {ticker}: {e}")

    # 2. Calculate RS Ratings
    rs_df = calculate_relative_strength(stock_data)
    
    results = []
    
    print("\n--- Analyzing Stocks ---")
    for ticker, df in stock_data.items():
        if df is None: continue
        
        current_price = df['Close'].iloc[-1]
        try:
            rs = rs_df.loc[ticker, 'RS_Rating']
        except KeyError:
            continue
        
        if check_trend_template(df, current_price, rs):
            vcp = analyze_volatility_contraction(df)
            
            # Entry: Breakout of 20 day high
            pivot_point = df['High'].iloc[-20:].max()
            
            # Stop Loss: 8% below entry or Low of last 5 days (tighter)
            stop_loss = current_price * 0.92 
            
            # Save Chart
            chart_path = save_minervini_chart(ticker, df, today_str)
            
            # Collect Data
            results.append({
                "Date": today_str,
                "Ticker": ticker,
                "Price": round(current_price, 2),
                "RS_Rating": int(rs),
                "Trend_Status": "Stage 2 Confirmed",
                "VCP_Condition": "Tight" if vcp else "Normal",
                "Buy_Point_Pivot": round(pivot_point, 2),
                "Stop_Loss": round(stop_loss, 2),
                "Chart_Path": chart_path
            })
            print(f"Saved candidate: {ticker}")

    # 3. Export to Excel
    if results:
        report_file = f"{REPORTS_DIR}/Minervini_Screen_{today_str}.xlsx"
        final_df = pd.DataFrame(results)
        final_df.to_excel(report_file, index=False)
        print(f"\n✅ SUCCESS! Report saved to: {report_file}")
        print(f"✅ Charts saved in: {CHARTS_DIR}/")
    else:
        print("\nNo stocks met the criteria today.")
