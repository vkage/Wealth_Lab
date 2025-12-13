from .base import MomentumStrategy
import utils.technical_indicators as ta
import pandas as pd
from utils.visualization import plot_minervini_chart

class MinerviniStrategy(MomentumStrategy):
    @property
    def name(self) -> str:
        return "Minervini Trend Template"

    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        if data is None or len(data) < 260: # Need 52 weeks
            print(f"Minervini Fail {ticker}: len={len(data) if data is not None else 'None'}")
            return {
                "status": "FAIL",
                "signal": "NEUTRAL",
                "score": 0,
                "details": [f"Insufficient Data ({len(data) if data is not None else 0} < 260 days)"],
                "metrics": {},
                "chart_path": None
            }

        # Indicators
        # Ensure we have data for calc
        df = data.copy()
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['SMA_150'] = ta.sma(df['Close'], length=150)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['52_Week_Low'] = df['Close'].rolling(window=260).min()
        df['52_Week_High'] = df['Close'].rolling(window=260).max()
        
        # Check if indicators are valid (not all NaN)
        curr = df.iloc[-1]
        if pd.isna(curr['SMA_200']):
             return {
                "status": "FAIL",
                "signal": "NEUTRAL",
                "score": 0,
                "details": ["Insufficient Data for Indicators"],
                "metrics": {},
                "chart_path": None
            }

        price = curr['Close']
        pass_reasons = []
        fail_reasons = []
        passed_conditions = 0
        total_conditions = 8

        # Helper
        def fmt(val): return f"{val:.2f}"

        # 1. Price > 150 & 200 SMA
        if price > curr['SMA_150'] and price > curr['SMA_200']:
            pass_reasons.append(f"Price ({fmt(price)}) > 150 & 200 SMA")
            passed_conditions += 1
        else:
            fail_reasons.append(f"Price ({fmt(price)}) below 150/200 SMA")

        # 2. 150 SMA > 200 SMA
        if curr['SMA_150'] > curr['SMA_200']:
            pass_reasons.append("150 SMA > 200 SMA (Long Term Uptrend)")
            passed_conditions += 1
        else:
            fail_reasons.append("150 SMA < 200 SMA")

        # 3. 200 SMA Trending Up (Lookback 20 days)
        prev_200 = df['SMA_200'].iloc[-21]
        if curr['SMA_200'] > prev_200:
            pass_reasons.append("200 SMA Trending Up")
            passed_conditions += 1
        else:
            fail_reasons.append("200 SMA Flattening/Falling")

        # 4. 50 SMA > 150 & 200
        if curr['SMA_50'] > curr['SMA_150'] and curr['SMA_50'] > curr['SMA_200']:
            pass_reasons.append("50 SMA > 150 & 200 SMA (Medium Trend Strong)")
            passed_conditions += 1
        else:
            fail_reasons.append("50 SMA below 150/200 SMA")

        # 5. Price > 50 SMA
        if price > curr['SMA_50']:
            pass_reasons.append("Price > 50 SMA")
            passed_conditions += 1
        else:
            fail_reasons.append("Price < 50 SMA")

        # 6. 30% above 52-Week Low
        low_threshold = 1.3 * curr['52_Week_Low']
        if price >= low_threshold:
            pct_above = ((price - curr['52_Week_Low']) / curr['52_Week_Low']) * 100
            pass_reasons.append(f"Above 52W Low (+{fmt(pct_above)}%)")
            passed_conditions += 1
        else:
            fail_reasons.append(f"Too close to 52W Low ({fmt(curr['52_Week_Low'])})")

        # 7. Within 25% of 52-Week High
        high_threshold = 0.75 * curr['52_Week_High']
        if price >= high_threshold:
            pct_below = ((curr['52_Week_High'] - price) / curr['52_Week_High']) * 100
            pass_reasons.append(f"Near 52W High (-{fmt(pct_below)}%)")
            passed_conditions += 1
        else:
            fail_reasons.append(f"Too far from 52W High ({fmt(curr['52_Week_High'])})")

        # 8. RSI >= 50 (Bonus/Trend Strength)
        if curr['RSI'] >= 50:
            pass_reasons.append(f"RSI Bullish ({fmt(curr['RSI'])})")
            passed_conditions += 1
        else:
            fail_reasons.append(f"RSI Weak ({fmt(curr['RSI'])})")

        # DECISION
        # Strict Minervini requires almost all, but let's say 7/8 is a pass, or 8/8 strict?
        # Let's keep it strict: Must meet Trend conditions (1-5) + High/Low (6-7). RSI is bonus.
        # Simplification: If Fail reasons is empty, PASS.
        # Logic from original: "PASS" if not fail_reasons.
        
        status = "PASS" if len(fail_reasons) == 0 else "FAIL"
        signal = "BUY" if status == "PASS" else "NEUTRAL"

        # Chart Generation
        # OLD: chart_path = plot_minervini_chart(ticker, df)
        # NEW: Return JSON
        from utils.visualization import create_minervini_figure
        fig = create_minervini_figure(ticker, df)
        chart_json = fig.to_json()

        return {
            "strategy": self.name,
            "status": status,
            "signal": signal,
            "score": f"{passed_conditions}/{total_conditions}",
            "details": pass_reasons if status == "PASS" else fail_reasons, 
            "all_details": {"pass": pass_reasons, "fail": fail_reasons},
            "metrics": {
                "Price": price,
                "RSI": curr['RSI'],
                "SMA_50": curr['SMA_50'],
                "Pivot": df['High'].iloc[-20:].max()
            },
            "chart_json": chart_json
        }
