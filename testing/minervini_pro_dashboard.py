import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import os
import glob
import json
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
TICKER_LIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "BAJFINANCE.NS",
    "MARUTI.NS", "ADANIENT.NS", "SUNPHARMA.NS", "TITAN.NS", "HAL.NS",
    "KPITTECH.NS", "TRENT.NS", "BEL.NS", "VBL.NS", "ZOMATO.NS",
    "YESBANK.NS", "IDEA.NS" , "DIVISLAB.NS", "LALPATHLAB.NS",
    "BAJAJHFL.NS", "TATAELXSI.NS", "HDFCGOLD.NS", "NESTLEIND.NS", "GMMPFAUDLR.NS",
    "EICHERMOT.NS", "M&M.NS", "CLEAN.NS"
]

# Folders
REPORTS_DIR = "minervini_reports"
DATA_DIR = "stock_data_cache"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

LOOKBACK_YEARS = 2

# ==========================================
# 2. DATA ENGINE (With Caching)
# ==========================================
def fetch_data(ticker):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cache_file = f"{DATA_DIR}/{ticker}_{today_str}.csv"
    
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty: return df
        except: pass

    try:
        start_date = datetime.datetime.now() - datetime.timedelta(days=LOOKBACK_YEARS*365)
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if not df.empty:
            df.to_csv(cache_file)
            # Cleanup old files
            for f in glob.glob(f"{DATA_DIR}/{ticker}_*.csv"):
                if today_str not in f: os.remove(f)
            return df
    except Exception as e:
        print(f"Error {ticker}: {e}")
        
    return None

# ==========================================
# 3. ANALYSIS LOGIC
# ==========================================
def calculate_metrics(df):
    if len(df) < 200: return None
    
    # SMAs
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_150'] = ta.sma(df['Close'], length=150)
    df['SMA_200'] = ta.sma(df['Close'], length=200)
    
    # Momentum
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']
    
    # 52 Week Stats
    df['52_Week_Low'] = df['Close'].rolling(window=260).min()
    df['52_Week_High'] = df['Close'].rolling(window=260).max()
    df['SMA_200_Trending'] = df['SMA_200'] > df['SMA_200'].shift(20)
    
    return df

def check_minervini_criteria(df, rs_rating):
    curr = df.iloc[-1]
    price = curr['Close']
    reasons = []
    
    # Criteria Checks
    if not (price > curr['SMA_150'] and price > curr['SMA_200']):
        reasons.append("Price below 150/200 SMA")
    if not (curr['SMA_150'] > curr['SMA_200']):
        reasons.append("150 SMA not above 200 SMA")
    if not curr['SMA_200_Trending']:
        reasons.append("200 SMA not trending up")
    if not (curr['SMA_50'] > curr['SMA_150'] and curr['SMA_50'] > curr['SMA_200']):
        reasons.append("50 SMA not above 150/200 SMA")
    if not (price > curr['SMA_50']):
        reasons.append("Price below 50 SMA")
    if not (price >= 1.3 * curr['52_Week_Low']):
        reasons.append("Not 30% above 52-wk Low")
    if not (price >= 0.75 * curr['52_Week_High']):
        reasons.append("More than 25% below 52-wk High")
    if not (rs_rating >= 70):
        reasons.append(f"RS Rating too low ({int(rs_rating)})")
        
    return reasons

# ==========================================
# 4. CHART GENERATION (Plotly)
# ==========================================
def generate_interactive_chart(ticker, df):
    # Filter last 1 year
    plot_df = df.iloc[-250:].copy()
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{ticker} Price Action", "RSI (14)", "MACD"))

    # 1. Candlestick & MA
    fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'],
                                 low=plot_df['Low'], close=plot_df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA_50'], line=dict(color='blue', width=1), name='50 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA_150'], line=dict(color='orange', width=1), name='150 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA_200'], line=dict(color='black', width=1.5), name='200 SMA'), row=1, col=1)

    # 2. RSI
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI'], line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # 3. MACD
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD'], line=dict(color='blue'), name='MACD'), row=3, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD_Signal'], line=dict(color='orange'), name='Signal'), row=3, col=1)
    fig.add_trace(go.Bar(x=plot_df.index, y=plot_df['MACD']-plot_df['MACD_Signal'], marker_color='gray', name='Hist'), row=3, col=1)

    fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
    
    # Return DIV string for HTML embedding
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

# ==========================================
# 5. HTML DASHBOARD BUILDER
# ==========================================
def generate_html_report(passed, rejected, date_str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Minervini Momentum Dashboard - {date_str}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .card {{ box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: none; margin-bottom: 20px; }}
            .header-bg {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 2rem 0; margin-bottom: 2rem; }}
            .status-pass {{ color: #198754; font-weight: bold; }}
            .status-fail {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header-bg">
            <div class="container">
                <h1>🚀 Minervini Momentum Dashboard</h1>
                <p>Date: {date_str} | Market: NSE India</p>
            </div>
        </div>

        <div class="container">
            <ul class="nav nav-pills mb-3" id="pills-tab" role="tablist">
                <li class="nav-item"><button class="nav-link active" data-bs-toggle="pill" data-bs-target="#pills-pass" type="button">✅ Passed Stocks ({len(passed)})</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#pills-fail" type="button">❌ Rejected Stocks ({len(rejected)})</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#pills-charts" type="button">📈 Interactive Charts</button></li>
            </ul>

            <div class="tab-content" id="pills-tabContent">
                
                <div class="tab-pane fade show active" id="pills-pass">
                    <div class="card p-3">
                        <table id="passTable" class="table table-striped table-hover" style="width:100%">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Price</th>
                                    <th>RS Rating</th>
                                    <th>Pivot (Buy)</th>
                                    <th>Stop Loss</th>
                                    <th>RSI</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f"<tr><td><b>{p['Ticker']}</b></td><td>{p['Price']}</td><td>{p['RS_Rating']}</td><td>{p['Pivot']}</td><td>{p['Stop_Loss']}</td><td>{p['RSI']}</td><td><button class='btn btn-sm btn-primary' onclick=\"showChart('{p['Ticker']}')\">View Chart</button></td></tr>" for p in passed])}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="tab-pane fade" id="pills-fail">
                    <div class="card p-3">
                        <table id="failTable" class="table table-striped table-hover" style="width:100%">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Price</th>
                                    <th>RS Rating</th>
                                    <th>Rejection Reasons</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f"<tr><td><b>{r['Ticker']}</b></td><td>{r['Price']}</td><td>{r['RS_Rating']}</td><td><span class='badge bg-danger'>{', '.join(r['Reasons'][:2])}</span> {( '...' if len(r['Reasons'])>2 else '')}</td></tr>" for r in rejected])}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="tab-pane fade" id="pills-charts">
                    <div class="card p-3">
                        <h4 class="mb-3">Stock Analysis Charts</h4>
                        <select class="form-select mb-3" id="chartSelector" onchange="renderSelectedChart()">
                            <option selected>Select a stock...</option>
                            {''.join([f"<option value='chart_{p['Ticker']}'>{p['Ticker']}</option>" for p in passed])}
                        </select>
                        <div id="chartContainer">
                            {''.join([f"<div id='chart_{p['Ticker']}' class='chart-div' style='display:none'>{p['Chart_HTML']}</div>" for p in passed])}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        
        <script>
            $(document).ready(function () {{
                $('#passTable').DataTable();
                $('#failTable').DataTable();
            }});

            function showChart(ticker) {{
                // Switch tab
                var someTabTriggerEl = document.querySelector('#pills-tab button[data-bs-target="#pills-charts"]')
                var tab = new bootstrap.Tab(someTabTriggerEl)
                tab.show()
                
                // Select dropdown
                document.getElementById('chartSelector').value = 'chart_' + ticker;
                renderSelectedChart();
            }}

            function renderSelectedChart() {{
                var selectedId = document.getElementById('chartSelector').value;
                var charts = document.getElementsByClassName('chart-div');
                for (var i = 0; i < charts.length; i++) {{
                    charts[i].style.display = 'none';
                }}
                if (document.getElementById(selectedId)) {{
                    document.getElementById(selectedId).style.display = 'block';
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    with open("minervini_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ Dashboard generated: minervini_dashboard.html")

# ==========================================
# 6. MAIN ORCHESTRATOR
# ==========================================
def main():
    print("--- Starting Professional Minervini Analysis ---")
    
    # 1. Fetch & Calculate
    stock_data = {}
    for ticker in TICKER_LIST:
        print(f"Fetching {ticker}...", end="\r")
        df = fetch_data(ticker)
        # To avoid hitting API limits
        time.sleep(1)  
        if df is not None:
            stock_data[ticker] = calculate_metrics(df)
    print("\nData fetch complete.")

    # 2. RS Rating
    # (Simplified RS calculation for demo speed)
    rs_scores = {}
    for t, df in stock_data.items():
        if df is None: continue
        try:
            chg = (df['Close'].iloc[-1] - df['Close'].iloc[-63]) / df['Close'].iloc[-63]
            rs_scores[t] = chg
        except: pass
    
    rs_df = pd.DataFrame.from_dict(rs_scores, orient='index', columns=['Score'])
    rs_df['Rank'] = rs_df['Score'].rank(pct=True) * 99
    
    # 3. Categorize
    passed_list = []
    rejected_list = []
    
    print("Analyzing stocks against Minervini rules...")
    for ticker, df in stock_data.items():
        if df is None: continue
        
        rs = rs_df.loc[ticker, 'Rank'] if ticker in rs_df.index else 0
        reasons = check_minervini_criteria(df, rs)
        current_price = round(df['Close'].iloc[-1], 2)
        
        if not reasons:
            # IT PASSED
            chart_html = generate_interactive_chart(ticker, df)
            passed_list.append({
                "Ticker": ticker,
                "Price": current_price,
                "RS_Rating": int(rs),
                "RSI": round(df['RSI'].iloc[-1], 2),
                "Pivot": round(df['High'].iloc[-20:].max(), 2),
                "Stop_Loss": round(current_price * 0.92, 2),
                "Chart_HTML": chart_html
            })
        else:
            # IT FAILED
            rejected_list.append({
                "Ticker": ticker,
                "Price": current_price,
                "RS_Rating": int(rs),
                "Reasons": reasons
            })

    # 4. Generate Reports
    generate_html_report(passed_list, rejected_list, datetime.datetime.now().strftime("%Y-%m-%d"))
    
    # Save Excel for records
    if passed_list:
        pd.DataFrame(passed_list).drop(columns=['Chart_HTML']).to_excel(f"{REPORTS_DIR}/Passed_Stocks.xlsx", index=False)
    if rejected_list:
        # Convert list of reasons to string for Excel
        rej_df = pd.DataFrame(rejected_list)
        rej_df['Reasons'] = rej_df['Reasons'].apply(lambda x: ", ".join(x))
        rej_df.to_excel(f"{REPORTS_DIR}/Rejected_Stocks.xlsx", index=False)

    print(f"\nAnalysis Complete!")
    print(f"Passed: {len(passed_list)} | Rejected: {len(rejected_list)}")
    print("OPEN 'minervini_dashboard.html' TO VIEW RESULTS.")

if __name__ == "__main__":
    main()