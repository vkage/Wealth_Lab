from flask import Flask, render_template, request, jsonify
from strategies.manager import StrategyManager
from strategies.portfolio_manager import PortfolioManager
from nse_tickers import NSE_TICKERS
import pandas as pd
import os
import threading

from utils.logger import setup_logger
from utils.db import get_db

app = Flask(__name__)
logger = setup_logger('app')
manager = StrategyManager()
portfolio_mgr = PortfolioManager()

# --- ROUTES ---

@app.route('/')
def home():
    # Landing page - Dashboard
    summaries = portfolio_mgr.get_all_portfolios_summary()
    metrics = portfolio_mgr.get_dashboard_metrics()
    return render_template('dashboard.html', portfolios=summaries, metrics=metrics)

@app.route('/portfolio')
def portfolio_view():
    pid = request.args.get('pid', type=int) # None = All
    if not pid and request.args.get('pid') != '0':
         # Default to 1 if no param, BUT we want "All" view support too.
         # Let's say pid=0 is ALL? Or no param is Default(1)?
         # User asked for "separate portfolios" and "All Portfolio tab".
         # Let's say: No param -> Load Default (1) or Last Active?
         # Let's start with Default (1).
         # Special value 'all' or 0 -> Aggregated.
         pid = 1 
    
    if request.args.get('pid') == 'all':
        pid = None

    stocks = portfolio_mgr.load_portfolio(portfolio_id=pid)
    # Summary calculation also needs update if we want summary per portfolio?
    # For now, summary logic inside mgr uses view which is global. 
    # We might need to recalc summary in python if pid is specific.
    # The current `get_portfolio_summary` uses `portfolio_view` which aggregates EVERYTHING.
    # TODO: Update summary logic for filtering.
    summary = {
        "total_invested": sum(s['invested_value'] for s in stocks),
        "current_value": sum(s['current_value'] for s in stocks),
        "stock_count": len(stocks)
    }
    summary["total_pnl"] = summary["current_value"] - summary["total_invested"]
    summary["total_pnl_pct"] = (summary["total_pnl"] / summary["total_invested"] * 100) if summary["total_invested"] > 0 else 0 
    
    portfolios = portfolio_mgr.get_portfolios()
    
    current_portfolio_name = "All Portfolios"
    if pid:
        for p in portfolios:
            if p.id == pid:
                current_portfolio_name = p.name
                break
    
    return render_template('portfolio.html', stocks=stocks, summary=summary, portfolios=portfolios, current_pid=pid if pid else 'all', current_ptf_name=current_portfolio_name)

@app.route('/analyze_ticker', methods=['GET'])
def analyze_ticker_api():
    """API to analyze a single ticker (used by UI via AJAX)"""
    ticker = request.args.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker provided"})
    
    # Just in case simple correction
    if not (ticker.endswith(".NS") or ticker.endswith(".BO") or ticker.startswith("^")):
        ticker += ".NS"
        
    result = manager.analyze_ticker(ticker)
    
    # NEW: Cache the result for portfolio view persistence
    try:
        portfolio_mgr.save_analysis(ticker, result)
    except Exception as e:
        print(f"Failed to cache analysis for {ticker}: {e}")

    return jsonify(result)

@app.route('/api/portfolios', methods=['GET', 'POST'])
def handle_portfolios():
    if request.method == 'POST':
        data = request.json
        pid = portfolio_mgr.create_portfolio(data['name'])
        return jsonify({"success": pid is not None, "id": pid})
    else:
        # GET
        ports = portfolio_mgr.get_portfolios()
        return jsonify([{"id": p.id, "name": p.name} for p in ports])

@app.route('/api/portfolios/<int:pid>/rename', methods=['POST'])
def rename_portfolio(pid):
    data = request.json
    success = portfolio_mgr.rename_portfolio(pid, data['name'])
    return jsonify({"success": success})

@app.route('/add_stock', methods=['POST'])
def add_stock_route():
    try:
        data = request.json
        ticker = data.get('ticker')
        qty = float(data.get('quantity'))
        price = float(data.get('avg_price'))
        pid = data.get('portfolio_id', 1)
        # Phase 13: Purchase Date
        p_date = data.get('purchase_date') # ISO string YYYY-MM-DD or empty
        
        pm = PortfolioManager()
        success, msg = pm.add_stock(ticker, qty, price, pid, purchase_date=p_date)
        
        if success:
            return jsonify({"status": "success", "message": msg})
        else:
            return jsonify({"status": "error", "message": msg}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/edit_stock_date', methods=['POST'])
def edit_stock_date_route():
    try:
        data = request.json
        ticker = data.get('ticker')
        pid = data.get('portfolio_id')
        new_date = data.get('date')
        
        pm = PortfolioManager()
        success = pm.edit_stock_date(ticker, pid, new_date)
        
        if success:
             return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Update failed"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    data = request.json
    pid = data.get('portfolio_id', 1)
    success = portfolio_mgr.remove_stock(data['ticker'], portfolio_id=pid)
    return jsonify({"success": success})
@app.route('/watchlist')
def watchlist_view():
    db = get_db()
    session = db.get_db_session()
    
    watchlist_data = []
    try:
        from models import Watchlist
        # Fetch all tickers
        tickers = [r.ticker for r in session.query(Watchlist).all()]
        
        # Analyze each
        for t in tickers:
            try:
                res = manager.analyze_ticker(t)
                
                # Extract Key Metrics
                price = res.get('price', 0)
                summary = res.get('summary', {})
                strategies = res.get('strategies', {})
                
                min_res = strategies.get('Minervini Trend Template', {})
                min_status = min_res.get('status', 'FAIL')
                
                # Action & Momentum Health
                if min_status == 'PASS':
                    comp_health = "Strong Buy"
                    action = "BUY"
                    health_class = "text-green-400"
                    action_class = "bg-green-600 text-white"
                else:
                    # Check if it's mixed or weak (reusing logic or simple check)
                    # For now simplifed:
                    comp_health = "Weak"
                    action = "AVOID"
                    health_class = "text-red-400"
                    action_class = "bg-red-600 text-white"
                    
                # Upside Calculation
                upside_txt = "N/A"
                upside_class = "text-gray-500"
                target_type = "-"
                
                # Only calc upside if decent health (or strict rule?)
                # User said: "If Momentum Health is PASS ... Otherwise N/A or Avoid" (Initial)
                # Updated Plan: Always show selection rule?
                # "Selection Rule: If price within 5% of 52W High..."
                
                # Let's get data for 52W High
                # Minervini details usually have it, or metrics
                metrics = min_res.get('metrics', {})
                # We need raw data if metrics don't have 52W High. 
                # Minervini metrics in `minervini.py` currently returns Price, RSI, SMA_50, Pivot.
                # It does NOT return 52W High explicitly in metrics dict.
                # However, we can re-analyze or fetch. 
                # Optimization: `manager.analyze_ticker` fetches data. We could modify Minervini to return it, 
                # or just fetch here if efficiency isn't huge issue (it is cached by manager?). 
                # Actually manager implementation creates fresh `fetch_stock_data`.
                
                # Hack: Parse 52W High from details string if present? No, unreliable.
                # Better: Access the `data` used in strategy? Strategy doesn't expose it.
                # Quick Fix: Fetch single point data or leverage the fact we can calculate it?
                # Let's trust `min_res['chart_json']`? No.
                
                # We will fetch basics again or update Minervini strategy.
                # Updating Strategy is cleaner but requires editing another file.
                # For now, let's just fetch history for 1y to get 52W High quickly.
                # (Or since we just analyzed it, maybe we update Minervini.py to include 52W High/Low in metrics)
                
                # Let's assume we update Minervini.py in next step or use separate fetch.
                # I'll stick to separate fetch for minimal invasion now (or update strategy which is better).
                # Actually, I will update Minervini.py to return 52W High in metrics. 
                # But I can't do that effectively in this single tool call if I didn't plan it.
                # I'll use `utils.data_loader` here to get 52W High.
                from utils.data_loader import fetch_stock_data
                df = fetch_stock_data(t, period="1y")
                
                if df is not None and not df.empty:
                    high_52 = df['High'].max()
                    current = df['Close'].iloc[-1]
                    pivot = df['High'].iloc[-20:].max()
                    
                    # Logic
                    # Secondary Target (Minervini)
                    min_target = pivot * 1.20
                    
                    # Selection Rule
                    # If current price is within 5% of (or above) 52-Week High
                    is_near_high = current >= (high_52 * 0.95)
                    
                    if min_status == 'PASS':
                        if is_near_high:
                             target = min_target
                             target_label = "Momentum (Pivot+20%)"
                        else:
                             target = high_52
                             target_label = "Resistance (52W High)"
                             
                        # Calculate Upside
                        if target > current:
                            pot = ((target - current) / current) * 100
                            upside_txt = f"+{pot:.1f}%"
                            upside_class = "text-green-400"
                        elif target == current:
                             upside_txt = "0%"
                        else:
                             upside_txt = "Blue Sky"
                             upside_class = "text-blue-400"
                        
                        # Formatting
                        upside_txt = f"{upside_txt} <span class='text-xs text-gray-500 block'>{target_label}</span>"
                    else:
                        upside_txt = "-"
                        upside_class = "text-gray-600"

                watchlist_data.append({
                    "ticker": t,
                    "price": price,
                    "health": comp_health,
                    "health_class": health_class,
                    "action": action,
                    "action_class": action_class,
                    "upside": upside_txt,
                    "upside_class": upside_class
                })

            except Exception as e:
                print(f"Error processing {t}: {e}")
                
    finally:
        db.close_session()

    return render_template('watchlist.html', stocks=watchlist_data)

@app.route('/api/watchlist/add', methods=['POST'])
def add_watchlist():
    data = request.json
    ticker = data.get('ticker', '').strip().upper()
    if not ticker: return jsonify({"success": False, "error": "No ticker"})
    
    # Correction
    if not (ticker.endswith(".NS") or ticker.endswith(".BO") or ticker.startswith("^")):
        ticker += ".NS"

    # VALIDATION STEP
    try:
        import yfinance as yf
        # Check if we can fetch recent data
        # 'period="1mo"' is light enough. If empty, it's likely invalid/delisted.
        df = yf.download(ticker, period="5d", progress=False)
        if df is None or df.empty:
             return jsonify({"success": False, "error": f"Invalid or delisted ticker: {ticker}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to validate ticker: {str(e)}"})

    db = get_db()
    session = db.get_db_session()
    try:
        from models import Watchlist
        # Check exist
        if not session.query(Watchlist).filter_by(ticker=ticker).first():
            new_item = Watchlist(ticker=ticker)
            session.add(new_item)
            session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        db.close_session()

@app.route('/api/watchlist/remove', methods=['POST'])
def remove_watchlist():
    data = request.json
    ticker = data.get('ticker')
    
    db = get_db()
    session = db.get_db_session()
    try:
        from models import Watchlist
        item = session.query(Watchlist).filter_by(ticker=ticker).first()
        if item:
            session.delete(item)
            session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        db.close_session()


if __name__ == '__main__':
    print("Starting WealthLab App...")
    app.run(debug=True, port=5000)