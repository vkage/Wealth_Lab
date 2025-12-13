from strategies.portfolio_manager import PortfolioManager
import json
import os

def migrate():
    print("Starting migration...")
    pm = PortfolioManager()
    # This triggers the load, which triggers the import_from_excel -> save_portfolio flow if JSON is missing.
    # If JSON exists, it loads that. 
    # To be safe, if we want to ensure we captured the Excel state as "starting point", 
    # we might want to check if JSON exists. 
    # But the user said "keep current stocks", which implies whatever is currently visible (which comes from Excel mostly as we just added it).
    
    stocks = pm.load_portfolio()
    print(f"Loaded {len(stocks)} stocks.")
    
    if os.path.exists("portfolio/user_portfolio.json"):
        print("user_portfolio.json exists.")
        with open("portfolio/user_portfolio.json", 'r') as f:
            data = json.load(f)
            print(f"JSON contains {len(data)} items.")
    else:
        print("ERROR: user_portfolio.json was NOT created.")

if __name__ == "__main__":
    migrate()
