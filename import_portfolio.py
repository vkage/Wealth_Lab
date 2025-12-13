import pandas as pd
import sys
import os
from strategies.portfolio_manager import PortfolioManager
from utils.logger import setup_logger

logger = setup_logger('importer')

def import_portfolio(file_path):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        print(f"Error: File {file_path} not found.")
        return

    try:
        logger.info(f"Reading Excel file: {file_path}")
        df = pd.read_excel(file_path)
        
        # Expected columns: Stock, Holdings, Buy_price
        required_cols = ['Stock', 'Holdings', 'Buy_price']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Missing columns. Required: {required_cols}")
            print(f"Error: Excel must have columns: {required_cols}")
            return

        pm = PortfolioManager()
        success_count = 0
        fail_count = 0

        for index, row in df.iterrows():
            ticker = str(row['Stock']).strip()
            try:
                qty = float(row['Holdings'])
                price = float(row['Buy_price'])
                
                if pm.add_stock(ticker, qty, price):
                    logger.info(f"Successfully added/updated {ticker}")
                    success_count += 1
                else:
                    logger.error(f"Failed to add {ticker}")
                    fail_count += 1
            except Exception as e:
                logger.error(f"Error processing row {index} ({ticker}): {e}")
                fail_count += 1

        summary = f"Import Complete. Success: {success_count}, Failed: {fail_count}"
        logger.info(summary)
        print(summary)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_portfolio.py <path_to_excel_file>")
    else:
        import_portfolio(sys.argv[1])
