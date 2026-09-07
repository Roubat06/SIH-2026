import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'sentinel.db')

def get_db_path() -> str:
    path = os.getenv('DATABASE_PATH', DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path

def get_connection() -> sqlite3.Connection:
    path = get_db_path()
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode = WAL;')
    conn.execute('PRAGMA synchronous = NORMAL;')
    return conn

@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def now():
    return datetime.now(timezone.utc).isoformat()

def public(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        d = dict(row)
    elif isinstance(row, dict):
        d = dict(row)
    else:
        return row
    d.pop('password_hash', None)
    return d

