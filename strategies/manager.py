from .minervini import MinerviniStrategy
from .dual_momentum import DualMomentumStrategy
from utils.data_loader import fetch_stock_data
from concurrent.futures import ThreadPoolExecutor

class StrategyManager:
    def __init__(self):
        self.strategies = [
            MinerviniStrategy(),
            DualMomentumStrategy() # Default args
        ]
    
    def analyze_ticker(self, ticker: str):
        """
        Runs all strategies for a single ticker.
        """
        data = fetch_stock_data(ticker, period="5y")
        
        if data is None or data.empty:
             return {
                "ticker": ticker,
                "error": "Data Not Found",
                "results": {}
            }

        results = {}
        overall_score = 0
        total_strategies = len(self.strategies)
        passed_strategies = 0
        
        current_price = data['Close'].iloc[-1]
        
        for strategy in self.strategies:
            try:
                res = strategy.analyze(ticker, data)
                results[strategy.name] = res
                if res['status'] == 'PASS':
                    passed_strategies += 1
            except Exception as e:
                print(f"Strategy {strategy.name} failed for {ticker}: {e}")
                results[strategy.name] = {"status": "ERROR", "details": [str(e)]}

        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "summary": {
                "strategies_passed": f"{passed_strategies}/{total_strategies}",
                "bullish": passed_strategies == total_strategies,
                "bearish": passed_strategies == 0
            },
            "strategies": results
        }

    def analyze_batch(self, tickers: list):
        """Parallel analysis for a list of tickers."""
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            full_results = list(executor.map(self.analyze_ticker, tickers))
            results.extend(full_results)
        return results
