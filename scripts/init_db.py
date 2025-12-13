import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='mysql.db')

TABLES = {}

TABLES['portfolio'] = (
    "CREATE TABLE IF NOT EXISTS portfolio ("
    "  id INT AUTO_INCREMENT PRIMARY KEY,"
    "  ticker VARCHAR(20) NOT NULL UNIQUE,"
    "  quantity DECIMAL(15, 4) NOT NULL DEFAULT 0,"
    "  avg_price DECIMAL(15, 4) NOT NULL DEFAULT 0,"
    "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
    "  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
    ") ENGINE=InnoDB"
)

TABLES['market_data'] = (
    "CREATE TABLE IF NOT EXISTS market_data ("
    "  ticker VARCHAR(20) NOT NULL,"
    "  date DATE NOT NULL,"
    "  open_price DECIMAL(15, 4),"
    "  high_price DECIMAL(15, 4),"
    "  low_price DECIMAL(15, 4),"
    "  close_price DECIMAL(15, 4),"
    "  volume BIGINT,"
    "  PRIMARY KEY (ticker, date),"
    "  INDEX idx_date (date)"
    ") ENGINE=InnoDB"
)

TABLES['stock_details'] = (
    "CREATE TABLE IF NOT EXISTS stock_details ("
    "  ticker VARCHAR(20) PRIMARY KEY,"
    "  company_name VARCHAR(255),"
    "  sector VARCHAR(100),"
    "  market_cap BIGINT,"
    "  pe_ratio DECIMAL(10, 2),"
    "  book_value DECIMAL(10, 2),"
    "  fifty_two_week_high DECIMAL(15, 4),"
    "  fifty_two_week_low DECIMAL(15, 4),"
    "  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
    ") ENGINE=InnoDB"
)

TABLES['analysis_cache'] = (
    "CREATE TABLE IF NOT EXISTS analysis_cache ("
    "  ticker VARCHAR(20) NOT NULL,"
    "  strategy_name VARCHAR(50) NOT NULL,"
    "  result_json JSON,"
    "  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
    "  PRIMARY KEY (ticker, strategy_name)"
    ") ENGINE=InnoDB"
)

VIEWS = {}
VIEWS['portfolio_view'] = (
    "CREATE OR REPLACE VIEW portfolio_view AS "
    "SELECT "
    "    p.ticker,"
    "    p.quantity,"
    "    p.avg_price,"
    "    (p.quantity * p.avg_price) AS invested_value,"
    "    m.close_price AS current_price,"
    "    (p.quantity * m.close_price) AS current_value,"
    "    ((p.quantity * m.close_price) - (p.quantity * p.avg_price)) AS pnl,"
    "    m.date AS price_date "
    "FROM portfolio p "
    "LEFT JOIN ("
    "    SELECT t1.ticker, t1.close_price, t1.date "
    "    FROM market_data t1 "
    "    INNER JOIN ("
    "        SELECT ticker, MAX(date) as max_date "
    "        FROM market_data "
    "        GROUP BY ticker"
    "    ) t2 ON t1.ticker = t2.ticker AND t1.date = t2.max_date"
    ") m ON p.ticker = m.ticker"
)

def create_database():
    try:
        # Connect to server directly to create DB if not exists
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'password')
        )
        cursor = conn.cursor()
        db_name = os.getenv('DB_NAME', 'momentum_analysis')
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database {db_name} ensured.")
        
        conn.database = db_name
        
        for name, ddl in TABLES.items():
            print(f"Creating table {name}...")
            cursor.execute(ddl)
            
        for name, ddl in VIEWS.items():
            print(f"Creating view {name}...")
            cursor.execute(ddl)
            
        conn.close()
        print("Database initialization complete.")
        return True
    except mysql.connector.Error as err:
        print(f"Failed to initialize database: {err}")
        return False

if __name__ == '__main__':
    create_database()
