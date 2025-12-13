import pandas as pd
from sqlalchemy import text
from utils.db import get_db
from models import Portfolio, AnalysisCache 
import json

class PortfolioManager:
    def __init__(self):
        pass



    def get_portfolios(self):
        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolios
            return session.query(Portfolios).all()
        finally:
            db.close_session()

    def create_portfolio(self, name):
        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolios
            new_p = Portfolios(name=name)
            session.add(new_p)
            session.commit()
            return new_p.id
        except:
            session.rollback()
            return None
        finally:
            db.close_session()

    def rename_portfolio(self, pid, name):
        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolios
            p = session.query(Portfolios).filter_by(id=pid).first()
            if p:
                p.name = name
                session.commit()
                return True
            return False
        finally:
            db.close_session()

    def load_portfolio(self, portfolio_id=None):
        """Loads portfolio. if portfolio_id is None, loads ALL (aggregated)."""
        db = get_db()
        session = db.get_db_session()
        try:
            # We need to compute values manually since VIEW might not be updated yet.
            # Or assume we just list stocks.
            # Let's perform a query joining Portfolio + MarketData
            from models import Portfolio, MarketData
            from sqlalchemy import func as sa_func
            
            # Subquery: Latest date per ticker
            subq = session.query(
                MarketData.ticker,
                sa_func.max(MarketData.date).label('max_date')
            ).group_by(MarketData.ticker).subquery()
            
            # Subquery: Latest Close Price
            latest_prices = session.query(
                MarketData.ticker,
                MarketData.close_price
            ).join(
                subq,
                (MarketData.ticker == subq.c.ticker) & (MarketData.date == subq.c.max_date)
            ).subquery()
            
            q = session.query(
                Portfolio.ticker, 
                Portfolio.quantity, 
                Portfolio.avg_price, 
                Portfolio.purchase_date, # Phase 13
                Portfolio.portfolio_id,
                latest_prices.c.close_price
            ).outerjoin(latest_prices, Portfolio.ticker == latest_prices.c.ticker)
            
            if portfolio_id:
                q = q.filter(Portfolio.portfolio_id == portfolio_id)
            
            results = q.all()
            
            # Also fetch names for ID mapping (if needed)
            
            rows = []
            for r in results:
                qty = float(r.quantity)
                avg = float(r.avg_price)
                curr_price = float(r.close_price) if r.close_price else avg # Fallback
                
                invested = qty * avg
                curr_val = qty * curr_price
                pnl = curr_val - invested
                pnl_pct = (pnl / invested * 100) if invested > 0 else 0
                
                rows.append({
                    "ticker": r.ticker,
                    "quantity": qty,
                    "avg_price": avg,
                    "current_price": curr_price,
                    "invested_value": invested,
                    "current_value": curr_val,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "original_name": r.ticker, # Placeholder
                    "portfolio_id": r.portfolio_id,
                    "purchase_date": r.purchase_date.strftime("%Y-%m-%d") if r.purchase_date else None
                })
            
            # Attach Analysis (same logic as before)
            caches = session.query(AnalysisCache).all()
            cache_map = {}
            for c in caches:
                if c.result_json:
                    val = c.result_json
                    if isinstance(val, str): 
                        try: val = json.loads(val)
                        except: pass
                    cache_map[c.ticker] = val
            
            for row in rows:
                if row['ticker'] in cache_map:
                    row['analysis'] = cache_map[row['ticker']]

            self.stocks = rows
            return self.stocks
            
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            db.close_session()

    def add_stock(self, ticker, qty, avg_price, portfolio_id=1, purchase_date=None):
        ticker = ticker.strip().upper()
        if not (ticker.endswith(".NS") or ticker.endswith(".BO")): ticker += ".NS"
        
        # Default date to today if not provided
        import datetime
        if not purchase_date:
            txn_date = datetime.date.today()
        else:
            if isinstance(purchase_date, str):
                txn_date = datetime.datetime.strptime(purchase_date, "%Y-%m-%d").date()
            else:
                txn_date = purchase_date

        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolio, PortfolioTransaction
            
            # 1. Log Transaction
            new_txn = PortfolioTransaction(
                portfolio_id=portfolio_id,
                ticker=ticker,
                transaction_type='BUY',
                quantity=qty,
                price=avg_price,
                date=txn_date
            )
            session.add(new_txn)

            # 2. Update Portfolio
            existing = session.query(Portfolio).filter_by(ticker=ticker, portfolio_id=portfolio_id).first()
            if existing:
                # Calculate Weighted Average
                curr_qty = float(existing.quantity or 0)
                curr_avg = float(existing.avg_price or 0)
                
                new_total_qty = curr_qty + qty
                new_total_value = (curr_qty * curr_avg) + (qty * avg_price)
                if new_total_qty > 0:
                     new_avg_price = new_total_value / new_total_qty
                else: 
                     new_avg_price = 0
                
                existing.quantity = new_total_qty
                existing.avg_price = new_avg_price
                # Note: We do NOT overwrite purchase_date of existing stock (it retains original entry date)
                # Unless we want to track 'last_buy_date', but typically purchase_date = initial entry.
            else:
                new_stock = Portfolio(
                    ticker=ticker, 
                    quantity=qty, 
                    avg_price=avg_price, 
                    portfolio_id=portfolio_id,
                    purchase_date=txn_date
                )
                session.add(new_stock)
            
            session.commit()
            return True, "Stock Added"
        except Exception as e:
            session.rollback()
            print(f"Error adding stock: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
        finally:
            db.close_session()

    def edit_stock_date(self, ticker, portfolio_id, new_date):
        """Update the initial purchase date of a holding."""
        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolio
            existing = session.query(Portfolio).filter_by(ticker=ticker, portfolio_id=portfolio_id).first()
            if existing:
                if isinstance(new_date, str):
                    existing.purchase_date = datetime.datetime.strptime(new_date, "%Y-%m-%d").date()
                else:
                    existing.purchase_date = new_date
                session.commit()
                return True
            return False
        except Exception as e:
            print(f"Update Date Error: {e}")
            session.rollback()
            return False
        finally:
            db.close_session()

    def update_stock(self, ticker, qty, avg_price, portfolio_id=1):
        if qty <= 0: return self.remove_stock(ticker, portfolio_id)
        
        db = get_db()
        session = db.get_db_session()
        try:
            stock = session.query(Portfolio).filter_by(ticker=ticker, portfolio_id=portfolio_id).first()
            if stock:
                stock.quantity = qty
                stock.avg_price = avg_price
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            db.close_session()

    def remove_stock(self, ticker, portfolio_id=1):
        db = get_db()
        session = db.get_db_session()
        try:
            stock = session.query(Portfolio).filter_by(ticker=ticker, portfolio_id=portfolio_id).first()
            if stock:
                session.delete(stock)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            db.close_session()

    def get_all_portfolios_summary(self):
        """Returns list of summaries with sector breakdown."""
        db = get_db()
        session = db.get_db_session()
        try:
            from models import Portfolio, Portfolios, MarketData, StockDetails
            from sqlalchemy import func as sa_func, case

            # 1. Metric Aggregation (Value, PnL) - Same as before
            subq = session.query(
                MarketData.ticker,
                sa_func.max(MarketData.date).label('max_date')
            ).group_by(MarketData.ticker).subquery()

            latest_prices = session.query(
                MarketData.ticker,
                MarketData.close_price
            ).join(
                subq,
                (MarketData.ticker == subq.c.ticker) & (MarketData.date == subq.c.max_date)
            ).subquery()

            # Main Summary
            results = session.query(
                Portfolios.id,
                Portfolios.name,
                sa_func.count(Portfolio.ticker).label('stock_count'),
                sa_func.sum(Portfolio.quantity * Portfolio.avg_price).label('invested'),
                sa_func.sum(
                    Portfolio.quantity * 
                    case(
                        (latest_prices.c.close_price != None, latest_prices.c.close_price),
                        else_=Portfolio.avg_price
                    )
                ).label('current_val')
            ).outerjoin(
                Portfolio, Portfolios.id == Portfolio.portfolio_id
            ).outerjoin(
                latest_prices, Portfolio.ticker == latest_prices.c.ticker
            ).group_by(Portfolios.id, Portfolios.name).all()

            # 2. Sector Aggregation
            # Query: PortfolioID, Sector, Value
            sector_q = session.query(
                Portfolio.portfolio_id,
                sa_func.coalesce(StockDetails.sector, 'Unknown').label('sector'),
                sa_func.sum(
                    Portfolio.quantity * 
                    case(
                        (latest_prices.c.close_price != None, latest_prices.c.close_price),
                        else_=Portfolio.avg_price
                    )
                ).label('sec_val')
            ).outerjoin(
                latest_prices, Portfolio.ticker == latest_prices.c.ticker
            ).outerjoin(
                StockDetails, Portfolio.ticker == StockDetails.ticker
            ).group_by(Portfolio.portfolio_id, sa_func.coalesce(StockDetails.sector, 'Unknown')).all()

            # Map sectors to portfolio
            sec_map = {}
            for r in sector_q:
                pid = r.portfolio_id
                if pid not in sec_map: sec_map[pid] = []
                sec_map[pid].append({"label": r.sector, "value": float(r.sec_val or 0)})

            summaries = []
            for r in results:
                inv = float(r.invested or 0)
                curr = float(r.current_val or 0)
                pnl = curr - inv
                pct = (pnl / inv * 100) if inv > 0 else 0
                
                # Get sectors for this PID
                sectors = sec_map.get(r.id, [])
                # Calculate percentages
                total_sec_val = sum(s['value'] for s in sectors)
                if total_sec_val > 0:
                    for s in sectors: s['percent'] = round(s['value'] / total_sec_val * 100, 1)
                
                # Sort by value desc
                sectors.sort(key=lambda x: x['value'], reverse=True)

                summaries.append({
                    "id": r.id,
                    "name": r.name,
                    "count": r.stock_count,
                    "invested": inv,
                    "current": curr,
                    "pnl": pnl,
                    "pnl_pct": pct,
                    "sectors": sectors
                })
            
            return summaries
        except Exception as e:
            print(f"All Portfolios Summary Error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            db.close_session()

    def get_portfolio_summary(self):
        # Use simple aggregation on the VIEW query for consistency
        db = get_db()
        session = db.get_db_session()
        try:
            query = text("""
                SELECT 
                    SUM(invested_value) as total_invested,
                    SUM(current_value) as current_value,
                    COUNT(*) as stock_count
                FROM portfolio_view
            """)
            result = session.execute(query).fetchone()
            
            if result and result[0] is not None:
                ti = float(result[0])
                cv = float(result[1])
                pnl = cv - ti
                pct = (pnl / ti * 100) if ti > 0 else 0
                return {
                    "total_invested": ti,
                    "current_value": cv,
                    "total_pnl": pnl,
                    "total_pnl_pct": pct,
                    "stock_count": result[2]
                }
        except Exception as e:
            print(f"Summary Error: {e}")
        finally:
            db.close_session()
            
        return {"total_invested": 0, "current_value": 0, "total_pnl": 0, "total_pnl_pct": 0, "stock_count": 0}

    def save_analysis(self, ticker, result):
        simple_res = {
            "passed": result.get('summary', {}).get('strategies_passed', 'N/A'),
            "bullish": result.get('summary', {}).get('bullish', False),
            "bearish": result.get('summary', {}).get('bearish', False),
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        }
        
        db = get_db()
        session = db.get_db_session()
        try:
            # Merge (Insert or Update)
            # ORM merge uses PK.
            # AnalysisCache PK is (ticker, strategy_name)
            cache_entry = AnalysisCache(
                ticker=ticker,
                strategy_name='combined',
                result_json=simple_res # SQLAlchemy JSON type handles dict
            )
            session.merge(cache_entry)
            session.commit()
        except Exception as e:
            print(f"Save Analysis Error: {e}")
            session.rollback()
        finally:
            db.close_session()

    def get_dashboard_metrics(self):
        """Returns Benchmark Stats and Market Breadth."""
        metrics = {
            "benchmark": {"name": "Nifty 50", "price": 0, "change_1y": 0, "history": [], "status": "Neutral", "trend": "Sideways"},
            "breadth": {"total": 0, "bullish": 0, "bearish": 0, "neutral": 0, "label": "Daily Trend Breadth"}
        }
        
        # 1. Benchmark Data (Nifty 50)
        try:
            from utils.data_loader import fetch_benchmark_data
            # Fetch 2y to ensure valid 200 DMA
            df = fetch_benchmark_data(period="2y")
            
            if df is not None and not df.empty:
                # Latest Price & 1Y Change
                latest = float(df['Close'].iloc[-1])
                # Find approx 1 year ago (252 trading days)
                one_year_ago_idx = -252 if len(df) >= 252 else 0
                start_val = float(df['Close'].iloc[one_year_ago_idx])
                change = ((latest - start_val) / start_val) * 100
                
                # Trend Logic (Strict Minervini Strategy Reuse)
                try:
                    from strategies.minervini import MinerviniStrategy
                    strat = MinerviniStrategy()
                    # Minervini requires ~260 days. We fetched '2y' so we are good.
                    analysis = strat.analyze("^NSEI", df)
                    
                    status_raw = analysis.get('status', 'FAIL')
                    details = analysis.get('details', [])
                    
                    if status_raw == "PASS":
                        status = "Strong Buy"
                        trend = "Stage 2 Uptrend"
                    else:
                        # Analyze failure reasons to determine if it's Mixed or Weak
                        # If price is below 200 SMA -> Weak
                        # If just 52W High fail -> Accumulation/Mixed
                        
                        # Quick check on key technicals from the DF directly for classification
                        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
                        if latest < sma200:
                            status = "Weak"
                            trend = "Downtrend"
                        else:
                            # It failed Minervini (e.g. not near highs), but is above 200 SMA
                            status = "Accumulation"
                            trend = "Consolidation"
                            
                        # Append main failure reason to trend label for clarity
                        if details:
                            # simplify detail text
                            reason = details[0].split('(')[0].strip()
                            trend = f"{trend}: {reason}"

                except Exception as me:
                    print(f"Minervini Strat Error: {me}")
                    status = "Mixed"
                    trend = "Error Calc"

                # Resample for sparkline (last 1y only, ~250 points, downsampled)
                # Slice last 250 points first
                last_1y_df = df.iloc[-252:] if len(df) > 252 else df
                history = last_1y_df['Close'].iloc[::5].tolist()
                
                metrics['benchmark'] = {
                    "name": "Nifty 50",
                    "price": latest,
                    "change_1y": round(change, 2),
                    "history": [round(x, 2) for x in history],
                    "status": status,
                    "trend": trend
                }
        except Exception as e:
            print(f"Benchmark Error: {e}")

        # 2. Market Breadth
        db = get_db()
        session = db.get_db_session()
        try:
            from models import AnalysisCache, Portfolio
            import json
            
            # Get list of tickers currently in portfolio to filter cache
            portfolio_tickers = [t[0] for t in session.query(Portfolio.ticker).distinct().all()]
            
            # Query cache only for these tickers
            caches = session.query(AnalysisCache).filter(AnalysisCache.ticker.in_(portfolio_tickers)).all()
            
            total = 0
            bull = 0
            bear = 0
            
            for c in caches:
                if c.result_json:
                    total += 1
                    res = c.result_json
                    if isinstance(res, str): res = json.loads(res)
                    
                    is_bull = res.get('bullish', False)
                    is_bear = res.get('bearish', False)
                    
                    if is_bull: bull += 1
                    elif is_bear: bear += 1
            
            # Important: Use the portfolio_tickers count as total if we want to show GAP (unanalysed stocks)
            # OR just show analyzed count. User asked why counts mismatch.
            # Best approach: Total should be Total Analysed Portfolio Stocks.
            # If total < len(portfolio_tickers), it means some stocks haven't been scanned today.
            
            metrics['breadth'] = {
                "total": total,
                "bullish": bull,
                "bearish": bear,
                "neutral": total - (bull + bear),
                "label": "Daily Trend Breadth"  # Explicit Label
            }
        except Exception as e:
            print(f"Breadth Error: {e}")
        finally:
            db.close_session()
            
        return metrics
