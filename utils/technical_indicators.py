import pandas as pd

def sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=length).mean()

def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=length, min_periods=length).mean() # Init with SMA
    avg_loss = loss.rolling(window=length, min_periods=length).mean()
    
    # Wilder's Smoothing for subsequent values?
    # Keeping it simple with SMA method for robustness or EWM?
    # Standard RSI uses Wilder's Smoothing (EWM with alpha=1/length)
    # Let's match standard closer:
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Moving Average Convergence Divergence"""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'MACD_12_26_9': macd_line,
        'MACDs_12_26_9': signal_line,
        'MACDh_12_26_9': histogram
    })
