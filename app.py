from flask import Flask, render_template, request, jsonify
from strategies.manager import StrategyManager
from strategies.portfolio_manager import PortfolioManager
from nse_tickers import NSE_TICKERS
import pandas as pd
import os
import threading

from utils.logger import setup_logger

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
@app.route('/suggest')
def suggest_ticker():
    query = request.args.get('q', '').upper()
    suggestions = [t for t in NSE_TICKERS if query in t][:10] # Limit to 10
    return jsonify(suggestions)

if __name__ == '__main__':
    print("Starting Momentum Analysis App...")
    app.run(debug=True, port=5000)