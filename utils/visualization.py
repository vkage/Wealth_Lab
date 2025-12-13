import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import datetime

CHARTS_DIR = "static/charts"
os.makedirs(CHARTS_DIR, exist_ok=True)

def create_chart_filename(ticker: str, suffix: str = "") -> str:
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sanitized_ticker = ticker.replace("^", "").replace(".", "_").replace("&", "_and_")
    return f"{sanitized_ticker}_{suffix}_{timestamp_str}.html"

def save_chart(fig: go.Figure, filename: str) -> str:
    path = os.path.join(CHARTS_DIR, filename)
    fig.write_html(path)
    return filename

def create_minervini_figure(ticker: str, df: pd.DataFrame) -> go.Figure:
    """Creates the Minervini Figure object."""
    import utils.technical_indicators as ta
    if 'SMA_50' not in df.columns: df['SMA_50'] = ta.sma(df['Close'], length=50)
    if 'SMA_150' not in df.columns: df['SMA_150'] = ta.sma(df['Close'], length=150)
    if 'SMA_200' not in df.columns: df['SMA_200'] = ta.sma(df['Close'], length=200)
    if 'RSI' not in df.columns: df['RSI'] = ta.rsi(df['Close'], length=14)
    # MACD
    if 'MACD' not in df.columns:
        macd = ta.macd(df['Close'])
        if macd is not None:
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_Signal'] = macd['MACDs_12_26_9']

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{ticker} Analysis", "RSI", "MACD"))
    
    # Pre-convert to list to ensure standard JSON serialization (avoid bdata)
    dates = df.index.tolist()
    
    # Price
    fig.add_trace(go.Candlestick(x=dates, 
                                 open=df['Open'].tolist(), 
                                 high=df['High'].tolist(), 
                                 low=df['Low'].tolist(), 
                                 close=df['Close'].tolist(), 
                                 name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=df['SMA_50'].tolist(), line=dict(color='blue'), name='50 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=df['SMA_150'].tolist(), line=dict(color='orange'), name='150 SMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=df['SMA_200'].tolist(), line=dict(color='black'), name='200 SMA'), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=dates, y=df['RSI'].tolist(), line=dict(color='purple'), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # MACD
    if 'MACD' in df.columns:
        fig.add_trace(go.Scatter(x=dates, y=df['MACD'].tolist(), line=dict(color='blue'), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=dates, y=df['MACD_Signal'].tolist(), line=dict(color='orange'), name='Signal'), row=3, col=1)
        # For Bar, we calculate diff. Convert to list after.
        hist = (df['MACD'] - df['MACD_Signal']).tolist()
        fig.add_trace(go.Bar(x=dates, y=hist, marker_color='gray', name='Hist'), row=3, col=1)

    # Dark Mode Default Template (can be overridden by JS)
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_minervini_chart(ticker: str, df: pd.DataFrame) -> str:
    """Standard Minervini Chart (Price, SMAs, RSI, MACD) - Saves to File for Backward Compat"""
    fig = create_minervini_figure(ticker, df)
    filename = create_chart_filename(ticker, "minervini")
    return save_chart(fig, filename)

def create_relative_strength_figure(ticker: str, df: pd.DataFrame, benchmark_df: pd.DataFrame) -> go.Figure:
    """Creates the Dual Momentum Figure object."""
    # Align dates
    common_idx = df.index.intersection(benchmark_df.index)
    df_aligned = df.loc[common_idx]
    bench_aligned = benchmark_df.loc[common_idx]
    
    rs_line = df_aligned['Close'] / bench_aligned['Close']
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4],
                        subplot_titles=(f"{ticker} vs Benchmark", "Relative Strength Ratio"))
    
    dates = df_aligned.index.tolist()
    
    fig.add_trace(go.Scatter(x=dates, y=df_aligned['Close'].tolist(), name=ticker), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=rs_line.tolist(), line=dict(color='green'), name='RS (Stock/Nifty)'), row=2, col=1)
    
    rs_sma = rs_line.rolling(window=252).mean()
    fig.add_trace(go.Scatter(x=dates, y=rs_sma.tolist(), line=dict(color='white', dash='dot'), name='12-Mo RS SMA'), row=2, col=1)

    fig.update_layout(height=600, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_relative_strength(ticker: str, df: pd.DataFrame, benchmark_df: pd.DataFrame) -> str:
    """Plots RS - Saves to File"""
    fig = create_relative_strength_figure(ticker, df, benchmark_df)
    filename = create_chart_filename(ticker, "dual_momentum")
    return save_chart(fig, filename)
