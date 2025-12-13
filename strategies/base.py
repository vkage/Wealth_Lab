from abc import ABC, abstractmethod
import pandas as pd

class MomentumStrategy(ABC):
    """
    Abstract Base Class for Momentum Strategies.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the strategy."""
        pass

    @abstractmethod
    def analyze(self, ticker: str, data: pd.DataFrame) -> dict:
        """
        Analyze the stock data and return a result dictionary.
        
        Expected Return Format:
        {
            "status": "PASS" | "FAIL",
            "score": int (optional),
            "details": [ "List of pass/fail reasons" ],
            "metrics": { "key": "value" }, # Specifics like RSI, SMA values
            "signal": "BUY" | "SELL" | "NEUTRAL"
        }
        """
        pass
