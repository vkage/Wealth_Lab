import yfinance as yf
import pandas as pd
from sqlalchemy import func
from utils.db import get_db
from models import MarketData, StockDetails

BENCHMARK_TICKER = "^NSEI"

def fetch_stock_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    ticker = ticker.strip().upper()
    if not (ticker.endswith(".NS") or ticker.endswith(".BO") or ticker.startswith("^")):
        ticker += ".NS"
    
    db = get_db()
    if not db: return _fetch_direct(ticker, period)
    
    session = db.get_db_session()
    try:
        # Check max date
        last_date = session.query(func.max(MarketData.date)).filter_by(ticker=ticker).scalar()
        
        if last_date:
            today = pd.Timestamp.now().date()
            if last_date < today:
                # Fetch missing
                new_data = yf.download(ticker, start=last_date + pd.Timedelta(days=1), progress=False, auto_adjust=True)
                if not new_data.empty:
                    _save_to_db(session, ticker, new_data)
            
            # Ensure StockDetails exist (Sector, etc.)
            try:
                if not session.query(StockDetails.ticker).filter_by(ticker=ticker).scalar():
                     _save_details(session, ticker)
            except Exception:
                pass

            # Return from DB
            return _load_from_db(session, ticker)
        
        # Else fetch full
        df = _fetch_direct(ticker, period)
        if df is not None:
             _save_to_db(session, ticker, df)
             _save_details(session, ticker)
        return df

    except Exception as e:
        print(f"Fetch Error {ticker}: {e}")
        return _fetch_direct(ticker, period) # Fallback
    finally:
        db.close_session()

def _fetch_direct(ticker, period):
    try:
        # yfinance might return MultiIndex columns keys: (Price, Ticker)
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        
        if df is None or df.empty:
            return None
            
        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            # Check if we have a level for Ticker
            if df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)
        
        return df
    except: return None

def _load_from_db(session, ticker):
    # Construct DF from query
    data = session.query(MarketData).filter_by(ticker=ticker).order_by(MarketData.date.asc()).all()
    if not data: return None
    
    records = []
    for d in data:
        records.append({
            'date': d.date,
            'Open': float(d.open_price),
            'High': float(d.high_price),
            'Low': float(d.low_price),
            'Close': float(d.close_price),
            'Volume': int(d.volume)
        })
        
    df = pd.DataFrame(records)
    if df.empty: return None
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def _save_to_db(session, ticker, df):
    # Batch create objects
    for idx, row in df.iterrows():
        # Handle potential Series if row keys return Series (rare if flattened but safe)
        def _val(x):
            if hasattr(x, 'iloc'): return float(x.iloc[0])
            return float(x)
        
        try:
            m = MarketData(
                ticker=ticker,
                date=idx.date(),
                open_price=_val(row['Open']),
                high_price=_val(row['High']),
                low_price=_val(row['Low']),
                close_price=_val(row['Close']),
                volume=int(_val(row['Volume']))
            )
            session.merge(m)
        except Exception: pass
    
    session.commit()

def _save_details(session, ticker):
    try:
        info = yf.Ticker(ticker).info
        d = StockDetails(
            ticker=ticker,
            company_name=info.get('longName', ''),
            sector=info.get('sector', ''),
            market_cap=info.get('marketCap', 0),
            pe_ratio=info.get('trailingPE', 0),
            book_value=info.get('bookValue', 0),
            fifty_two_week_high=info.get('fiftyTwoWeekHigh', 0),
            fifty_two_week_low=info.get('fiftyTwoWeekLow', 0)
        )
        session.merge(d)
        session.commit()
    except: pass

def fetch_benchmark_data(period: str = "5y") -> pd.DataFrame:
    return fetch_stock_data(BENCHMARK_TICKER, period)
