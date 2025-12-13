from strategies.manager import StrategyManager

def test_backend():
    print("Initializing Manager...")
    mgr = StrategyManager()
    
    ticker = "RELIANCE.NS"
    print(f"Analyzing {ticker}...")
    res = mgr.analyze_ticker(ticker)
    
    print("\n--- RESULTS ---")
    print(f"Ticker: {res['ticker']}")
    print(f"Price: {res['price']}")
    print(f"Summary: {res['summary']}")
    
    for name, data in res['strategies'].items():
        print(f"\nStrategy: {name}")
        print(f"Status: {data['status']}")
        print(f"Signal: {data.get('signal')}")
        print(f"Score: {data.get('score')}")
        if data['status'] == 'PASS':
            print("Passed Reasons:", data.get('details'))
        else:
            print("Failed Reasons:", data.get('details'))
            
    print("\nDone.")

if __name__ == "__main__":
    test_backend()
