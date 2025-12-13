import unittest
import pandas as pd
import utils.technical_indicators as ta
from strategies.minervini import MinerviniStrategy
from strategies.dual_momentum import DualMomentumStrategy
from unittest.mock import MagicMock, patch

class TestStrategies(unittest.TestCase):

    def setUp(self):
        # Create Dummy Data for Testing
        # 300 days of data
        dates = pd.date_range(start="2020-01-01", periods=300)
        self.data = pd.DataFrame(index=dates)
        # Create a uptrend: 10 to 310
        self.data['Close'] = [10 + i for i in range(300)]
        self.data['Open'] = self.data['Close']
        self.data['High'] = self.data['Close'] + 1
        self.data['Low'] = self.data['Close'] - 1
        
    def test_minervini_uptrend(self):
        """Test Minervini logic on a perfect uptrend."""
        strategy = MinerviniStrategy()
        
        # Calculate indicators needed for strategy validation within the test data
        # Actually strategy calculates them internally, so we just pass raw OHLC
        
        result = strategy.analyze("TEST", self.data)
        
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['signal'], 'BUY')
        self.assertTrue(len(result['details']) > 0)
        print("Minervini Uptrend Test: PASS")

    def test_minervini_downtrend(self):
        """Test Minervini logic on a downtrend."""
        dates = pd.date_range(start="2020-01-01", periods=300)
        data = pd.DataFrame(index=dates)
        # Downtrend: 310 to 10
        data['Close'] = [310 - i for i in range(300)]
        data['Open'] = data['Close']
        data['High'] = data['Close'] + 1
        data['Low'] = data['Close'] - 1
        
        strategy = MinerviniStrategy()
        result = strategy.analyze("TEST_DOWN", data)
        
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['signal'], 'NEUTRAL')
        print("Minervini Downtrend Test: PASS")

    def test_dual_momentum_pass(self):
        """Test Dual Momentum when Stock > Benchmark > 0."""
        strategy = DualMomentumStrategy()
        
        # Mock Benchmark: Flat return (start=100, end=100)
        dates = pd.date_range(start="2020-01-01", periods=300)
        bench_data = pd.DataFrame(index=dates)
        bench_data['Close'] = [100] * 300
        
        strategy._get_benchmark = MagicMock(return_value=bench_data)
        
        # Stock: Doubled (100 -> 200)
        stock_data = pd.DataFrame(index=dates)
        stock_data['Close'] = [100 + (i/3) for i in range(300)] # 100 to 200 approx
        
        result = strategy.analyze("TEST_DUAL", stock_data)
        
        self.assertEqual(result['status'], 'PASS')
        self.assertIn("Absolute Momentum Positive", result['details'][0])
        self.assertIn("Outperforming Benchmark", result['details'][1])
        print("Dual Momentum Pass Test: PASS")

    def test_dual_momentum_fail_rel(self):
        """Test Dual Momentum when Stock > 0 but Stock < Benchmark."""
        strategy = DualMomentumStrategy()
        
        dates = pd.date_range(start="2020-01-01", periods=300)
        
        # Benchmark: Tripled (100 -> 300)
        bench_data = pd.DataFrame(index=dates)
        bench_data['Close'] = [100 + (i*0.7) for i in range(300)]
        
        strategy._get_benchmark = MagicMock(return_value=bench_data)
        
        # Stock: Doubled (100 -> 200) - Positive but worse than bench
        stock_data = pd.DataFrame(index=dates)
        stock_data['Close'] = [100 + (i/3) for i in range(300)]
        
        result = strategy.analyze("TEST_DUAL_FAIL", stock_data)
        
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn("Underperforming Benchmark", result['details'][1])
        print("Dual Momentum Rel Fail Test: PASS")

if __name__ == '__main__':
    unittest.main()
