from datetime import datetime, timezone, timedelta
import pytest
from app.aml import AMLConfig, evaluate_aml_indicators


def test_aml_indicators_empty_or_normal():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    # Simple normal transaction: 2 inputs, 2 outputs, ordinary fees
    txs = [{
        "txid": "00" * 32,
        "observed_at": now.isoformat(),
        "block_time": now.isoformat(),
        "inputs": [{"prev_txid": "aa" * 32, "prev_vout": 0}],
        "outputs": [
            {"index": 0, "address": "addr_normal_1", "value_sats": 50_000_000, "script_type": "p2wpkh"},
            {"index": 1, "address": "addr_normal_2", "value_sats": 45_000_000, "script_type": "p2wpkh"},
        ],
        "fee_sats": 250,
        "vsize": 140,
    }]
    detections, scores = evaluate_aml_indicators(txs)
    assert len(detections[txs[0]["txid"]]) == 0
    assert scores[txs[0]["txid"]] == 0.0


def test_aml_fan_out_and_fan_in():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    fan_out_tx = {
        "txid": "01" * 32,
        "observed_at": now.isoformat(),
        "inputs": [{"prev_txid": "aa" * 32, "prev_vout": 0}],
        "outputs": [{"index": i, "address": f"addr_{i}", "value_sats": 10_000, "script_type": "p2wpkh"} for i in range(12)],
        "fee_sats": 500,
        "vsize": 350,
    }
    fan_in_tx = {
        "txid": "02" * 32,
        "observed_at": now.isoformat(),
        "inputs": [{"prev_txid": f"{i:02x}" * 32, "prev_vout": 0} for i in range(11)],
        "outputs": [{"index": 0, "address": "consolidation_addr", "value_sats": 100_000, "script_type": "p2wpkh"}],
        "fee_sats": 800,
        "vsize": 600,
    }
    detections, scores = evaluate_aml_indicators([fan_out_tx, fan_in_tx])
    codes_01 = [d["code"] for d in detections[fan_out_tx["txid"]]]
    codes_02 = [d["code"] for d in detections[fan_in_tx["txid"]]]
    assert "fan_out" in codes_01
    assert "fan_in" in codes_02
    assert scores[fan_out_tx["txid"]] >= 15.0
    assert scores[fan_in_tx["txid"]] >= 15.0


def test_aml_peeling_chain_and_rapid_movement():
    t0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)
    parent_tx = {
        "txid": "10" * 32,
        "observed_at": t0.isoformat(),
        "inputs": [{"prev_txid": "00" * 32, "prev_vout": 0}],
        "outputs": [
            {"index": 0, "address": "merchant_addr", "value_sats": 1_000_000, "script_type": "p2wpkh"},
            {"index": 1, "address": "peel_change_1", "value_sats": 99_000_000, "script_type": "p2wpkh"},
        ],
        "fee_sats": 500,
        "vsize": 140,
    }
    child_tx = {
        "txid": "11" * 32,
        "observed_at": t1.isoformat(),
        "inputs": [{"prev_txid": parent_tx["txid"], "prev_vout": 1}],
        "outputs": [
            {"index": 0, "address": "peel_payment_2", "value_sats": 2_000_000, "script_type": "p2wpkh"},
            {"index": 1, "address": "peel_change_2", "value_sats": 96_500_000, "script_type": "p2wpkh"},
        ],
        "fee_sats": 500,
        "vsize": 140,
    }
    detections, scores = evaluate_aml_indicators([parent_tx, child_tx])
    parent_codes = [d["code"] for d in detections[parent_tx["txid"]]]
    child_codes = [d["code"] for d in detections[child_tx["txid"]]]
    assert "aml_peeling_chain" in parent_codes
    assert "aml_peeling_chain" in child_codes
    assert "aml_rapid_movement" in child_codes


def test_aml_unusual_fee_ratio_and_volume():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    # Fee is 10,000 sats on a 50,000 sats output => 20% fee ratio (> 5% threshold)
    high_fee_tx = {
        "txid": "20" * 32,
        "observed_at": now.isoformat(),
        "inputs": [{"prev_txid": "aa" * 32, "prev_vout": 0}],
        "outputs": [{"index": 0, "address": "dest", "value_sats": 50_000, "script_type": "p2wpkh"}],
        "fee_sats": 10_000,
        "vsize": 140,
    }
    # Large volume transaction >= 5 BTC (500,000,000 sats)
    large_vol_tx = {
        "txid": "21" * 32,
        "observed_at": now.isoformat(),
        "inputs": [{"prev_txid": "bb" * 32, "prev_vout": 0}],
        "outputs": [{"index": 0, "address": "whale", "value_sats": 800_000_000, "script_type": "p2wpkh"}],
        "fee_sats": 1_000,
        "vsize": 140,
    }
    detections, scores = evaluate_aml_indicators([high_fee_tx, large_vol_tx])
    assert "aml_fee_ratio" in [d["code"] for d in detections[high_fee_tx["txid"]]]
    assert "aml_volume" in [d["code"] for d in detections[large_vol_tx["txid"]]]
