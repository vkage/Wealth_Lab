from sqlalchemy import Column, Integer, String, Float, Date, BigInteger, JSON, DateTime, Numeric
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

from sqlalchemy import ForeignKey, UniqueConstraint

class Portfolios(Base):
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Portfolio(Base):
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False, default=1)
    ticker = Column(String(20), nullable=False)
    quantity = Column(Numeric(15, 4), default=0)
    avg_price = Column(Numeric(15, 4), default=0)
    purchase_date = Column(Date) # Added for Phase 13
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (UniqueConstraint('portfolio_id', 'ticker', name='uix_portfolio_ticker'),)

class PortfolioTransaction(Base):
    __tablename__ = 'portfolio_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    ticker = Column(String(20), nullable=False)
    transaction_type = Column(String(10), nullable=False) # BUY, SELL
    quantity = Column(Numeric(15, 4), nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class MarketData(Base):
    __tablename__ = 'market_data'
    
    ticker = Column(String(20), primary_key=True)
    date = Column(Date, primary_key=True)
    open_price = Column(Numeric(15, 4))
    high_price = Column(Numeric(15, 4))
    low_price = Column(Numeric(15, 4))
    close_price = Column(Numeric(15, 4))
    volume = Column(BigInteger)

class StockDetails(Base):
    __tablename__ = 'stock_details'
    
    ticker = Column(String(20), primary_key=True)
    company_name = Column(String(255))
    sector = Column(String(100))
    market_cap = Column(BigInteger)
    pe_ratio = Column(Numeric(10, 2))
    book_value = Column(Numeric(10, 2))
    fifty_two_week_high = Column(Numeric(15, 4))
    fifty_two_week_low = Column(Numeric(15, 4))
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

class AnalysisCache(Base):
    __tablename__ = 'analysis_cache'
    
    ticker = Column(String(20), primary_key=True)
    strategy_name = Column(String(50), primary_key=True)
    result_json = Column(JSON)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
