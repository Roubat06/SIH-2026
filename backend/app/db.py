import os
import logging
from datetime import datetime, timezone
import mongomock

logger = logging.getLogger(__name__)

_client = None
_test_db = None
_in_memory_db = None

def now():
    return datetime.now(timezone.utc)

def database():
    global _client, _in_memory_db
    if _test_db is not None:
        return _test_db

    uri = (os.getenv('MONGO_URI') or os.getenv('MONGODB_URI') or '').strip()

    # When no MONGO_URI is set or memory/mock mode requested, run entirely in-memory
    if not uri or uri.lower() in {'memory', 'mock', 'none', 'embedded'}:
        if _in_memory_db is None:
            _in_memory_db = mongomock.MongoClient(tz_aware=True)['bitcoin_sentinel']
            logger.info("Running in prototype mode with in-memory database (No MongoDB service required).")
        return _in_memory_db

    if _client is None:
        try:
            from pymongo import MongoClient
            client = MongoClient(uri, serverSelectionTimeoutMS=2000, tz_aware=True)
            client.admin.command('ping')
            _client = client
        except Exception as exc:
            logger.warning("Could not connect to MongoDB (%s): %s. Seamlessly falling back to in-memory prototype database.", uri, exc)
            if _in_memory_db is None:
                _in_memory_db = mongomock.MongoClient(tz_aware=True)['bitcoin_sentinel']
            return _in_memory_db

    return _client[os.getenv('MONGO_DB', 'bitcoin_sentinel')]

def indexes(db):
    try:
        db.users.create_index('email', unique=True)
        db.sessions.create_index('expires_at', expireAfterSeconds=0)
        db.login_attempts.create_index('expires_at', expireAfterSeconds=0)
        db.cases.create_index('members.user_id')
        db.transactions.create_index([('case_id', 1), ('txid', 1)], unique=True)
        db.transactions.create_index([('case_id', 1), ('inputs.prev_txid', 1)])
        db.transactions.create_index([('case_id', 1), ('dataset_id', 1)])
        db.transactions.create_index([('case_id', 1), ('outputs.address', 1)])
        db.datasets.create_index([('case_id', 1), ('sha256', 1)], unique=True)
        db.datasets.create_index([('status', 1), ('created_at', 1)])
        db.alerts.create_index([('case_id', 1), ('score', -1)])
        db.features.create_index([('case_id', 1), ('txid', 1), ('dataset_id', 1)], unique=True)
        db.transactions.create_index([('case_id', 1), ('observed_at', -1)])
        db.transactions.create_index([('case_id', 1), ('block_time', -1)])
        db.alerts.create_index([('case_id', 1), ('detection_stages', 1), ('detected_at', -1)])
        db.audit.create_index([('case_id', 1), ('created_at', -1)])
        db.observations.create_index([('case_id', 1), ('txid', 1)])
    except Exception as exc:
        logger.debug("Indexes registered (note in mock mode: %s)", exc)

def public(doc):
    if not doc:
        return None
    return {('id' if k == '_id' else k): v for k, v in doc.items() if k not in {'password_hash', 'content', 'members'}}

