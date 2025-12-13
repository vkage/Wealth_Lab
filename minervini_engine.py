import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
REPORTS_DIR = "reports"
CHARTS_DIR = "static/charts"
MASTER_REPORT_FILE = os.path.join(REPORTS_DIR, "Master_Minervini_Log.xlsx")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# ==========================================
# DATA FUNCTIONS
# ==========================================
def fetch_stock_data(ticker):
    try:
        df = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def update_master_report(new_data_dict):
    new_df = pd.DataFrame([new_data_dict])
    if os.path.exists(MASTER_REPORT_FILE):
        try:
            existing_df = pd.read_excel(MASTER_REPORT_FILE)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_excel(MASTER_REPORT_FILE, index=False)
        except:
            new_df.to_excel(MASTER_REPORT_FILE, index=False)
    else:
        new_df.to_excel(MASTER_REPORT_FILE, index=False)

def get_execution_history():
    if not os.path.exists(MASTER_REPORT_FILE):
        return []
    try:
        df = pd.read_excel(MASTER_REPORT_FILE)
        df = df.sort_values(by="Timestamp", ascending=False)
        history = df.head(50).to_dict(orient='records')
        
        # Parse the text logs back into lists for the UI
        for item in history:
            item['pass_log'] = str(item.get('Detailed_Pass_Log', '')).split(" | ") if pd.notna(item.get('Detailed_Pass_Log')) else []
            item['fail_log'] = str(item.get('Reasons_If_Failed', '')).split(" | ") if pd.notna(item.get('Reasons_If_Failed')) else []
            
        return history
    except Exception as e:
        print(f"Error reading history: {e}")
        return []

# ==========================================
# CORE ANALYSIS ENGINE
# ==========================================
def analyze_stock(ticker):
    df = fetch_stock_data(ticker)
    
    if df is None or len(df) < 200:
        return {"status": "ERROR", "msg": "Insufficient Data (Need 200+ days)"}

    # 1. Indicators
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_150'] = ta.sma(df['Close'], length=150)
    df['SMA_200'] = ta.sma(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']
    
    df['52_Week_Low'] = df['Close'].rolling(window=260).min()
    df['52_Week_High'] = df['Close'].rolling(window=260).max()
    df['SMA_200_Trending'] = df['SMA_200'] > df['SMA_200'].shift(20)

    # 2. Logic & Reason Logging
    curr = df.iloc[-1]
    price = curr['Close']
    
    pass_reasons = [] # Log of PASSED criteria with values
    fail_reasons = [] # Log of FAILED criteria with values

    # Helper for formatting numbers
    def fmt(val): return f"{val:.2f}"

    # Rule 1: Price > 150 & 200 SMA
    if price > curr['SMA_150'] and price > curr['SMA_200']:
        pass_reasons.append(f"Price ({fmt(price)}) > 150/200 SMAs")
    else:
        fail_reasons.append(f"Price ({fmt(price)}) below SMAs")

    # Rule 2: 150 SMA > 200 SMA
    if curr['SMA_150'] > curr['SMA_200']:
        pass_reasons.append(f"150 SMA ({fmt(curr['SMA_150'])}) > 200 SMA ({fmt(curr['SMA_200'])})")
    else:
        fail_reasons.append("Long-term trend down (150 SMA < 200 SMA)")

    # Rule 3: 200 SMA Trending Up
    if curr['SMA_200_Trending']:
        pass_reasons.append("200 SMA is Trending UP")
    else:
        fail_reasons.append("200 SMA is flattening or falling")

    # Rule 4: 50 SMA > 150 & 200
    if curr['SMA_50'] > curr['SMA_150'] and curr['SMA_50'] > curr['SMA_200']:
        pass_reasons.append(f"50 SMA ({fmt(curr['SMA_50'])}) > 150/200 SMAs")
    else:
        fail_reasons.append("Medium trend weak (50 SMA misaligned)")

    # Rule 5: Price > 50 SMA
    if price > curr['SMA_50']:
        pass_reasons.append(f"Price ({fmt(price)}) > 50 SMA")
    else:
        fail_reasons.append("Price lost 50 SMA support")

    # Rule 6: 30% above 52-Week Low
    low_threshold = 1.3 * curr['52_Week_Low']
    if price >= low_threshold:
        pct_above = ((price - curr['52_Week_Low']) / curr['52_Week_Low']) * 100
        pass_reasons.append(f"Above Lows: +{fmt(pct_above)}% (Min 30%)")
    else:
        fail_reasons.append(f"Too close to lows ({fmt(curr['52_Week_Low'])})")

    # Rule 7: Near 52-Week High (Within 25%)
    high_threshold = 0.75 * curr['52_Week_High']
    if price >= high_threshold:
        pct_below = ((curr['52_Week_High'] - price) / curr['52_Week_High']) * 100
        pass_reasons.append(f"Near Highs: -{fmt(pct_below)}% (Max 25%)")
    else:
        fail_reasons.append(f"Deep in correction (High was {fmt(curr['52_Week_High'])})")

    # Rule 8: RSI
    if curr['RSI'] >= 50:
        pass_reasons.append(f"RSI Bullish ({fmt(curr['RSI'])})")
    else:
        fail_reasons.append(f"RSI Bearish ({fmt(curr['RSI'])})")

    # 3. Decision
    status = "PASS" if not fail_reasons else "FAIL"
    pivot = df['High'].iloc[-20:].max()
    stop_loss = price * 0.92

    # 4. Save Chart
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    display_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    chart_filename = f"{ticker}_{timestamp_str}.html"
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{ticker} ({status}) - {display_date}", "RSI", "MACD"))
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue'), name='50 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_150'], line=dict(color='orange'), name='150 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='black'), name='200 SMA'), row=1, col=1)
    fig.add_hline(y=pivot, line_dash="dot", line_color="green", annotation_text="Pivot", row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='blue'), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='orange'), name='Signal'), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACD']-df['MACD_Signal'], marker_color='gray', name='Hist'), row=3, col=1)
    
    fig.update_layout(height=800, template="plotly_white")
    fig.write_html(os.path.join(CHARTS_DIR, chart_filename))

    # 5. Save Report
    report_entry = {
        "Timestamp": display_date,
        "Ticker": ticker,
        "Status": status,
        "Price": round(price, 2),
        "Pivot_Buy_Point": round(pivot, 2),
        "Stop_Loss": round(stop_loss, 2),
        "RSI": round(curr['RSI'], 2),
        "Reasons_If_Failed": " | ".join(fail_reasons) if fail_reasons else "None",
        "Detailed_Pass_Log": " | ".join(pass_reasons), # NEW: Save passing reasons
        "Chart_Link": chart_filename
    }
    update_master_report(report_entry)

    return {
        "status": status,
        "ticker": ticker,
        "price": round(price, 2),
        "fail_reasons": fail_reasons,
        "pass_reasons": pass_reasons, # Send to UI
        "pivot": round(pivot, 2),
        "stop_loss": round(stop_loss, 2),
        "rsi": round(curr['RSI'], 2),
        "chart_url": f"charts/{chart_filename}"
    }