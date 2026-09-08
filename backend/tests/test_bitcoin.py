"""Tests for live Bitcoin API fetching with primary and alternate failover,

and in-memory prototype database operation without MongoDB.
"""
from datetime import datetime, timezone
import secrets
import pytest
from app.bitcoin import (
    get_bitcoin_endpoints,
    normalize_esplora_tx,
    fetch_fee_estimates,
    check_api_health,
    DEFAULT_PRIMARY_URL,
    DEFAULT_ALTERNATE_URL,
)
from app.db import database, public, now
from app.security import passwords
import app.db as db_module


def test_bitcoin_endpoints_contain_primary_and_alternate(monkeypatch):
    monkeypatch.setenv("BITCOIN_API_URL", "https://blockstream.info/api")
    endpoints = get_bitcoin_endpoints()
    assert endpoints[0] == "https://blockstream.info/api"
    assert DEFAULT_ALTERNATE_URL in endpoints
    assert len(endpoints) >= 2


def test_normalize_esplora_tx():
    raw_sample = {
        "txid": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "vin": [{"txid": "aa" * 32, "vout": 0}],
        "vout": [
            {"scriptpubkey_address": "bc1qtest1", "value": 100000, "scriptpubkey_type": "v0_p2wpkh"},
            {"scriptpubkey_address": "bc1qtest2", "value": 50000, "scriptpubkey_type": "v0_p2wpkh"},
        ],
        "fee": 2500,
        "weight": 560,
        "status": {
            "confirmed": True,
            "block_height": 850000,
            "block_time": 1720000000,
        },
    }
    normalized = normalize_esplora_tx(raw_sample)
    assert normalized["txid"] == raw_sample["txid"]
    assert len(normalized["inputs"]) == 1
    assert len(normalized["outputs"]) == 2
    assert normalized["fee_sats"] == 2500
    assert normalized["vsize"] == 140
    assert normalized["confirmed"] is True
    assert normalized["confirmations"] == 6


def test_fetch_fee_estimates_deterministic_or_live():
    fees = fetch_fee_estimates()
    assert "fastest_sat_vb" in fees
    assert "half_hour_sat_vb" in fees
    assert "hour_sat_vb" in fees
    assert fees["fastest_sat_vb"] >= fees["hour_sat_vb"]


def test_in_memory_db_without_mongodb(monkeypatch):
    # Ensure prototype operates without MONGO_URI
    monkeypatch.setenv("MONGO_URI", "")
    monkeypatch.setenv("MONGODB_URI", "")
    db = database()
    assert db is not None
    # Verify basic CRUD operations in prototype mode
    coll = db["test_prototype_records"]
    coll.insert_one({"test_key": "prototype_value", "created_at": now()})
    doc = coll.find_one({"test_key": "prototype_value"})
    assert doc is not None
    assert doc["test_key"] == "prototype_value"


def test_bitcoin_api_routes(client):
    # Create and authenticate user
    uid = secrets.token_hex(12)
    email = "investigator@example.org"
    password = "Strong-test-password-123"
    database().users.insert_one({
        "_id": uid,
        "email": email,
        "name": "Investigator",
        "role": "analyst",
        "password_hash": passwords.hash(password),
        "created_at": now(),
    })
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200

    # Create test case
    case_res = client.post("/api/cases", json={"name": "Live Bitcoin Test Case", "description": "Test"})
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]

    # 1. Status route
    status_res = client.get("/api/bitcoin/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "primary_url" in status_data
    assert "endpoints" in status_data

    # 2. Fee estimates route
    fees_res = client.get("/api/bitcoin/fee-estimates")
    assert fees_res.status_code == 200
    fees_data = fees_res.json()
    assert "fastest_sat_vb" in fees_data

    # 3. Live import to case (mocking live tx fetch)
    dummy_txid = "f" * 64

    # Post with mocked fetch
    import app.bitcoin_api as b_api

    def mock_fetch(txid):
        return {
            "txid": txid,
            "observed_at": "2026-09-01T12:00:00+00:00",
            "block_time": "2026-09-01T12:00:00+00:00",
            "inputs": [{"prev_txid": "0" * 64, "prev_vout": 0}],
            "outputs": [
                {"index": 0, "address": "bc1qsample1", "value_sats": 80000, "script_type": "p2wpkh"},
                {"index": 1, "address": "bc1qsample2", "value_sats": 15000, "script_type": "p2wpkh"},
            ],
            "fee_sats": 5000,
            "vsize": 140,
            "confirmed": True,
            "confirmations": 6,
            "api_source": "https://blockstream.info/api",
        }

    b_api.fetch_live_transaction = mock_fetch

    import_res = client.post(
        f"/api/cases/{case_id}/import-live",
        json={"txid": dummy_txid},
    )
    assert import_res.status_code == 200
    data = import_res.json()
    assert data["status"] == "success"
    assert data["imported_count"] == 1
    assert data["transactions"][0]["txid"] == dummy_txid
