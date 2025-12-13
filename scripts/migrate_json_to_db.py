import json
import os
from utils.db import execute_query

JSON_FILE = "portfolio/user_portfolio.json"

def migrate_data():
    if not os.path.exists(JSON_FILE):
        print("No JSON file found to migrate.")
        return

    try:
        with open(JSON_FILE, 'r') as f:
            stocks = json.load(f)
            
        print(f"Found {len(stocks)} stocks to migrate.")
        
        # Clear existing to avoid dupes during dev? Or use REPLACE INTO?
        # Using INSERT IGNORE or ON DUPLICATE KEY UPDATE
        
        cnt = 0
        for s in stocks:
            ticker = s.get('ticker')
            qty = s.get('quantity', 0)
            avg = s.get('avg_price', 0)
            
            query = """
                INSERT INTO portfolio (ticker, quantity, avg_price)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity=%s, avg_price=%s
            """
            res = execute_query(query, (ticker, qty, avg, qty, avg))
            if res: cnt += 1
            
        print(f"Successfully migrated {cnt} stocks.")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_data()
