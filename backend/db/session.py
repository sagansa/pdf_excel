import os
from sqlalchemy import create_engine, text

# Database configuration
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root') # Default MAMP
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306') # Default MAMP
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

SAGANSA_DB_USER = os.environ.get('SAGANSA_DB_USER', DB_USER)
SAGANSA_DB_PASS = os.environ.get('SAGANSA_DB_PASS', DB_PASS)
SAGANSA_DB_HOST = os.environ.get('SAGANSA_DB_HOST', DB_HOST)
SAGANSA_DB_PORT = os.environ.get('SAGANSA_DB_PORT', DB_PORT)
SAGANSA_DB_NAME = os.environ.get('SAGANSA_DB_NAME', 'sagansa')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SAGANSA_DB_URL = f"mysql+pymysql://{SAGANSA_DB_USER}:{SAGANSA_DB_PASS}@{SAGANSA_DB_HOST}:{SAGANSA_DB_PORT}/{SAGANSA_DB_NAME}"
# Base URL without database name to allow creating the database
DB_BASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}"
_db_engine = None
_db_last_error = None
_sagansa_engine = None
_sagansa_last_error = None

def get_db_engine():
    global _db_engine, _db_last_error
    if _db_engine is None:
        try:
            # First, try to connect to the specific database
            _db_engine = create_engine(DB_URL)
            # Test connection
            with _db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _db_last_error = None
        except Exception as e:
            # If the database doesn't exist, try to create it
            if "Unknown database" in str(e) or "database exists" in str(e) or "1049" in str(e):
                try:
                    print(f"Database '{DB_NAME}' not found. Attempting to create it...")
                    temp_engine = create_engine(DB_BASE_URL)
                    with temp_engine.connect() as conn:
                        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
                        conn.commit()
                    # Now try connecting again
                    _db_engine = create_engine(DB_URL)
                    _db_last_error = None
                except Exception as create_err:
                    _db_last_error = f"Database creation failed: {str(create_err)}"
                    _db_engine = None
            else:
                _db_last_error = f"Connection failed: {str(e)}"
                _db_engine = None
    return _db_engine, _db_last_error


def get_sagansa_engine():
    """
    Dedicated connection for Sagansa database.
    This connection is read-only from app logic perspective and does not auto-create DB.
    """
    global _sagansa_engine, _sagansa_last_error
    if _sagansa_engine is None:
        try:
            _sagansa_engine = create_engine(SAGANSA_DB_URL)
            with _sagansa_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _sagansa_last_error = None
        except Exception as e:
            _sagansa_last_error = f"Sagansa DB connection failed: {str(e)}"
            _sagansa_engine = None
    return _sagansa_engine, _sagansa_last_error
