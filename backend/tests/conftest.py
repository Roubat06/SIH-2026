import os
import secrets
import mongomock
import pytest
from fastapi.testclient import TestClient
from app import db
from app.main import app


@pytest.fixture
def client():
    real_uri = os.getenv('SENTINEL_TEST_MONGO_URI')
    real_client = None
    if real_uri:
        from pymongo import MongoClient
        real_client = MongoClient(real_uri, tz_aware=True)
        db._test_db = real_client['sentinel_test_' + secrets.token_hex(8)]
    else:
        db._test_db = mongomock.MongoClient(tz_aware=True).sentinel_test
    with TestClient(app) as c:
        c.headers['X-Sentinel-Request'] = '1'
        yield c
    if real_client is not None:
        real_client.drop_database(db._test_db.name)
        real_client.close()
    db._test_db = None
