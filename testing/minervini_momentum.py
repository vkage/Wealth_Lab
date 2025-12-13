import yfinance as yf
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import datetime
import os
import glob

# ==========================================
# CONFIGURATION
# ==========================================
TICKER_LIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "BAJFINANCE.NS",
    "MARUTI.NS", "ADANIENT.NS", "SUNPHARMA.NS", "TITAN.NS", "HAL.NS",
    "KPITTECH.NS", "TRENT.NS", "BEL.NS", "VBL.NS", "ZOMATO.NS"
]

# Folders for outputs and cache
CHARTS_DIR = "minervini_charts"
REPORTS_DIR = "minervini_reports"
DATA_DIR = "stock_data_cache"

for folder in [CHARTS_DIR, REPORTS_DIR, DATA_DIR]:
    os.makedirs(folder, exist_ok=True)

LOOKBACK_YEARS = 2

# ==========================================
# DATA MANAGEMENT (With Caching)
# ==========================================
def fetch_data(ticker):
    """
    Fetches data from cache if available for today, otherwise downloads from Yahoo Finance.
    """
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cache_file = f"{DATA_DIR}/{ticker}_{today_str}.csv"
    
    # 1. Check Cache
    if os.path.exists(cache_file):
        # Read from CSV
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        # Verify it has data
        if not df.empty:
            return df

    # 2. Download from Yahoo Finance
    start_date = datetime.datetime.now() - datetime.timedelta(days=LOOKBACK_YEARS*365)
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        
        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if not df.empty:
            # 3. Save to Cache
            df.to_csv(cache_file)
            # Clean up old cache files for this ticker to save space
            cleanup_old_cache(ticker, today_str)
            return df
            
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        
    return None

def cleanup_old_cache(ticker, current_date_str):
    """Removes csv files for the ticker that don't match today's date."""
    files = glob.glob(f"{DATA_DIR}/{ticker}_*.csv")
    for f in files:
        if current_date_str not in f:
            try:
                os.remove(f)
            except OSError:
                pass

# ==========================================
# METRICS & SCREENING
# ==========================================
def calculate_minervini_metrics(df):
    if len(df) < 200: return None

    # Trend Indicators
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_150'] = ta.sma(df['Close'], length=150)
    df['SMA_200'] = ta.sma(df['Close'], length=200)

    # Momentum Indicators (For Charts)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']

    # Minervini Criteria Helpers
    df['52_Week_Low'] = df['Close'].rolling(window=260).min()
    df['52_Week_High'] = df['Close'].rolling(window=260).max()
    df['SMA_200_Trending'] = df['SMA_200'] > df['SMA_200'].shift(20)

    return df

def calculate_relative_strength(stocks_df):
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

    if not rs_scores: return pd.DataFrame()

    rs_df = pd.DataFrame.from_dict(rs_scores, orient='index', columns=['Raw_Score'])
    rs_df['RS_Rating'] = rs_df['Raw_Score'].rank(pct=True) * 99
    return rs_df

def check_trend_template(df, current_price, rs_rating):
    if df is None or len(df) < 200: return False
    curr = df.iloc[-1]
    
    return (
        current_price > curr['SMA_150'] and 
        current_price > curr['SMA_200'] and
        curr['SMA_150'] > curr['SMA_200'] and 
        curr['SMA_200_Trending'] and
        curr['SMA_50'] > curr['SMA_150'] and 
        curr['SMA_50'] > curr['SMA_200'] and
        current_price > curr['SMA_50'] and
        current_price >= (1.30 * curr['52_Week_Low']) and
        current_price >= (0.75 * curr['52_Week_High']) and
        rs_rating >= 70
    )

def analyze_volatility_contraction(df):
    vol_10 = df['Close'].rolling(10).std().iloc[-1]
    vol_60 = df['Close'].rolling(60).std().iloc[-1]
    return vol_10 < (vol_60 * 0.5)

# ==========================================
# ADVANCED CHARTING
# ==========================================
def save_advanced_chart(ticker, df, today_str):
    """
    Saves a chart with Price, Volume, RSI, and MACD panels.
    """
    # Slice last 9 months for better visibility of recent momentum
    plot_df = df.iloc[-180:].copy()
    
    # 1. Moving Averages (Overlay on Price)
    apds = [
        mpf.make_addplot(plot_df['SMA_50'], color='blue', width=1.5),
        mpf.make_addplot(plot_df['SMA_150'], color='orange', width=1.5),
        mpf.make_addplot(plot_df['SMA_200'], color='black', width=2.0),
        
        # 2. RSI (Panel 2)
        mpf.make_addplot(plot_df['RSI'], panel=2, color='purple', ylabel='RSI (14)', ylim=(20, 80)),
        
        # 3. MACD (Panel 3)
        mpf.make_addplot(plot_df['MACD'], panel=3, color='green', ylabel='MACD'),
        mpf.make_addplot(plot_df['MACD_Signal'], panel=3, color='red'),
    ]
    
    filename = f"{CHARTS_DIR}/{ticker}_{today_str}_Momentum.png"
    
    # Create the plot with 3 panels: 0=Price, 1=Volume (default), 2=RSI, 3=MACD
    mpf.plot(
        plot_df, 
        type='candle', 
        style='yahoo', 
        volume=True, 
        addplot=apds,
        title=f'\nMinervini Momentum Setup: {ticker} ({today_str})',
        ylabel='Price (INR)',
        panel_ratios=(4, 1, 1, 1), # Adjust height ratio of panels
        tight_layout=True,
        savefig=filename
    )
    return filename

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("--- Starting Minervini Momentum Scanner (With Caching) ---")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    stock_data = {}
    
    print("1. Loading Data (Checking Cache first)...")
    for ticker in TICKER_LIST:
        df = fetch_data(ticker)
        if df is not None:
            stock_data[ticker] = calculate_minervini_metrics(df)

    print("2. Calculating Relative Strength...")
    rs_df = calculate_relative_strength(stock_data)
    
    results = []
    
    print("\n3. Analyzing & Generating Momentum Charts...")
    for ticker, df in stock_data.items():
        if df is None: continue
        
        current_price = df['Close'].iloc[-1]
        try:
            rs = rs_df.loc[ticker, 'RS_Rating']
        except KeyError: continue
        
        if check_trend_template(df, current_price, rs):
            vcp = analyze_volatility_contraction(df)
            pivot_point = df['High'].iloc[-20:].max()
            stop_loss = current_price * 0.92 
            
            # Save Advanced Chart
            chart_path = save_advanced_chart(ticker, df, today_str)
            
            results.append({
                "Date": today_str,
                "Ticker": ticker,
                "Price": round(current_price, 2),
                "RS_Rating": int(rs),
                "Trend": "Stage 2",
                "VCP": "Yes" if vcp else "No",
                "RSI": round(df['RSI'].iloc[-1], 2), # Add RSI to Excel
                "Entry_Pivot": round(pivot_point, 2),
                "Stop_Loss": round(stop_loss, 2),
                "Chart_File": chart_path
            })
            print(f"   -> Found & Charted: {ticker}")

    if results:
        report_file = f"{REPORTS_DIR}/Momentum_Screen_{today_str}.xlsx"
        pd.DataFrame(results).to_excel(report_file, index=False)
        print(f"\n✅ Done! Report: {report_file}")
        print(f"✅ Charts saved in '{CHARTS_DIR}' folder.")
        print(f"✅ Data cached in '{DATA_DIR}' folder.")
    else:
        print("\nNo stocks met the criteria today.")

if __name__ == "__main__":
    main()