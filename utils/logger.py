import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File Handler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'), 
            maxBytes=1024*1024*10, # 10MB
            backupCount=5
        )
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        logger.addHandler(console_handler)
        
    return logger
