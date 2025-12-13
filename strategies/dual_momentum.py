from .base import MomentumStrategy
import pandas as pd
from utils.visualization import plot_relative_strength
from utils.data_loader import fetch_benchmark_data

class DualMomentumStrategy(MomentumStrategy):
    def __init__(self, benchmark_ticker: str = "^NSEI", lookback_days: int = 252):
        self.benchmark_ticker = benchmark_ticker
        self.lookback_days = lookback_days
        # Cache benchmark data separately if needed, or fetch per call?
        # Fetching per call is safer for now to ensure alignment, cached by lru_cache in data_loader if we added it.
        # For now, explicit fetch.
        self.benchmark_data = None

    @property
    def name(self) -> str:
        return "Dual Momentum (Antonacci)"

    def _get_benchmark(self):
        if self.benchmark_data is None:
            self.benchmark_data = fetch_benchmark_data()
        return self.benchmark_data

    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        benchmark = self._get_benchmark()
        
        if data is None or len(data) < self.lookback_days:
             print(f"Dual Mom Fail {ticker}: len={len(data) if data is not None else 'None'}")
             return {
                 "status": "FAIL", 
                 "signal": "NEUTRAL", 
                 "details": [f"Insufficient Data ({len(data) if data is not None else 0} < {self.lookback_days})"], 
                 "metrics": {}, 
                 "score": "0/2", 
                 "chart_path": None
             }
        
        if benchmark is None or len(benchmark) < self.lookback_days:
             return {
                 "status": "FAIL", 
                 "signal": "NEUTRAL", 
                 "details": ["Benchmark Data Unavailable"], 
                 "metrics": {}, 
                 "score": "0/2", 
                 "chart_path": None
             }

        # Align Data
        common_idx = data.index.intersection(benchmark.index)
        if len(common_idx) < self.lookback_days:
            return {
                "status": "FAIL", 
                "signal": "NEUTRAL", 
                "details": ["Data Misalignment with Benchmark"], 
                "metrics": {}, 
                "score": "0/2", 
                "chart_path": None
            }
            
        stock_series = data.loc[common_idx]['Close']
        bench_series = benchmark.loc[common_idx]['Close']

        # 1. Absolute Momentum: 12-Month Return > Risk Free (0 for simplicity)
        curr_price = stock_series.iloc[-1]
        past_price = stock_series.iloc[-self.lookback_days]
        stock_return = (curr_price - past_price) / past_price
        
        abs_momentum_pass = stock_return > 0
        
        # 2. Relative Momentum: Stock Return > Benchmark Return
        curr_bench = bench_series.iloc[-1]
        past_bench = bench_series.iloc[-self.lookback_days]
        bench_return = (curr_bench - past_bench) / past_bench
        
        rel_momentum_pass = stock_return > bench_return
        
        status = "PASS" if (abs_momentum_pass and rel_momentum_pass) else "FAIL"
        
        details = []
        if abs_momentum_pass:
            details.append(f"Absolute Momentum Positive (+{stock_return:.1%})")
        else:
            details.append(f"Absolute Momentum Negative ({stock_return:.1%})")
            
        if rel_momentum_pass:
            details.append(f"Outperforming Benchmark ({stock_return:.1%} vs {bench_return:.1%})")
        else:
            details.append(f"Underperforming Benchmark ({stock_return:.1%} vs {bench_return:.1%})")

        # Chart
        # Chart
        # OLD: chart_path = plot_relative_strength(ticker, data, benchmark)
        from utils.visualization import create_relative_strength_figure
        fig = create_relative_strength_figure(ticker, data, benchmark)
        chart_json = fig.to_json()

        return {
            "strategy": self.name,
            "status": status,
            "signal": "BUY" if status == "PASS" else "SELL" if not abs_momentum_pass else "NEUTRAL",
            "score": f"{int(abs_momentum_pass) + int(rel_momentum_pass)}/2",
            "details": details,
            "metrics": {
                "Stock_1yr_Ret": f"{stock_return:.1%}",
                "Bench_1yr_Ret": f"{bench_return:.1%}",
                "Alpha": f"{(stock_return - bench_return):.1%}"
            },
            "chart_json": chart_json
        }
