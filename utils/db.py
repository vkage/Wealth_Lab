import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from utils.logger import setup_logger

load_dotenv(dotenv_path='mysql.db')

logger = setup_logger(__name__)

# Mocking the config object structure for compatibility with the user's requested style
# In a real scenario, this would import from core.configs
default_db = 'mysql'

def get_db_properties():
    return {
        'user': os.getenv('DB_USER', 'root'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'db': os.getenv('DB_NAME', 'momentum_analysis'),
        'password': os.getenv('DB_PASSWORD', '')
    }

def get_connection_string():
    props = get_db_properties()
    # mysql+pymysql://user:password@host/db_name
    return f"mysql+pymysql://{props['user']}:{props['password']}@{props['host']}/{props['db']}"

def mysql_engine():
    url = get_connection_string()
    # pool_recycle and pool_pre_ping for stability
    return create_engine(url, pool_recycle=3600, pool_pre_ping=True)

def get_session():
    engine = mysql_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

class DbConnector:
    def __init__(self):
        self.Session = None
        try:
            self.engine = mysql_engine()
            self._bind_tables()
            self.Session = sessionmaker(bind=self.engine)()
        except Exception as e:
            logger.error(f"Error in db initialization: {e}")

    def _bind_tables(self):
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

    def close_session(self):
        if self.Session:
            self.Session.close()

    def get_db_session(self):
        return self.Session

def get_db():
    try:
        return DbConnector()
    except Exception as e:
        logger.error(f"Error getting DB: {e}")
        return None
