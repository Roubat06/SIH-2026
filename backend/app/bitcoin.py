"""Live Bitcoin blockchain data fetching with free primary and alternate API failover.

Primary default: Blockstream Esplora API (https://blockstream.info/api)
Alternate: Mempool.space API (https://mempool.space/api)
Both are free public REST APIs requiring no paid subscription or API keys.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_PRIMARY_URL = "https://blockstream.info/api"
DEFAULT_ALTERNATE_URL = "https://mempool.space/api"


def get_bitcoin_endpoints() -> list[str]:
    """Return ordered list of free Bitcoin REST API base URLs."""
    primary = os.getenv("BITCOIN_API_URL", DEFAULT_PRIMARY_URL).strip().rstrip("/")
    if not primary:
        primary = DEFAULT_PRIMARY_URL
    endpoints = [primary]
    if DEFAULT_ALTERNATE_URL != primary:
        endpoints.append(DEFAULT_ALTERNATE_URL)
    return endpoints


def _request_with_failover(path: str, timeout: float = 6.0) -> tuple[Optional[httpx.Response], str]:
    """Attempt HTTP GET on primary endpoint; if failed, automatically try alternate."""
    endpoints = get_bitcoin_endpoints()
    last_error = None
    for endpoint in endpoints:
        url = f"{endpoint}{path}"
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                res = client.get(url, headers={"User-Agent": "Sentinel-Investigator/1.0"})
                if res.status_code == 200:
                    return res, endpoint
                logger.warning("Bitcoin API %s returned status %d. Attempting alternate if available.", url, res.status_code)
        except Exception as exc:
            logger.warning("Failed to connect to Bitcoin API %s: %s. Attempting alternate if available.", url, exc)
            last_error = exc

    return None, endpoints[0]


def check_api_health() -> dict[str, Any]:
    """Test health of primary and alternate Bitcoin APIs."""
    endpoints = get_bitcoin_endpoints()
    results = {}
    active_endpoint = None

    for ep in endpoints:
        status = "offline"
        tip_height = None
        latency_ms = None
        try:
            start = datetime.now(timezone.utc)
            with httpx.Client(timeout=4.0) as client:
                r = client.get(f"{ep}/blocks/tip/height")
                elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                if r.status_code == 200:
                    status = "ok"
                    tip_height = int(r.text.strip())
                    latency_ms = round(elapsed, 1)
                    if not active_endpoint:
                        active_endpoint = ep
        except Exception as e:
            status = f"error: {str(e)[:100]}"

        results[ep] = {
            "url": ep,
            "status": status,
            "free": True,
            "tip_height": tip_height,
            "latency_ms": latency_ms,
        }

    return {
        "primary_url": endpoints[0],
        "alternate_url": endpoints[1] if len(endpoints) > 1 else None,
        "active_endpoint": active_endpoint or "none (offline/mock fallback)",
        "endpoints": results,
    }


def normalize_esplora_tx(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert Esplora-format transaction JSON into Sentinel internal schema."""
    txid = raw.get("txid", "")
    status = raw.get("status", {})
    confirmed = status.get("confirmed", False)
    block_time_unix = status.get("block_time")
    block_dt = datetime.fromtimestamp(block_time_unix, timezone.utc) if block_time_unix else datetime.now(timezone.utc)
    block_iso = block_dt.isoformat()

    # Inputs
    inputs = []
    for vin in raw.get("vin", []):
        prev_txid = vin.get("txid") or ("00" * 32)
        prev_vout = vin.get("vout", 0)
        inputs.append({"prev_txid": prev_txid, "prev_vout": prev_vout})

    # Outputs
    outputs = []
    for idx, vout in enumerate(raw.get("vout", [])):
        addr = vout.get("scriptpubkey_address") or f"unknown_{idx}"
        val = vout.get("value", 0)
        stype = vout.get("scriptpubkey_type") or "p2wpkh"
        outputs.append({
            "index": idx,
            "address": addr,
            "value_sats": val,
            "script_type": stype,
        })

    fee_sats = raw.get("fee")
    weight = raw.get("weight") or (raw.get("size", 140) * 4)
    vsize = weight // 4 if weight else raw.get("size", 140)

    return {
        "txid": txid,
        "observed_at": block_iso,
        "block_time": block_iso if confirmed else None,
        "inputs": inputs,
        "outputs": outputs,
        "fee_sats": fee_sats,
        "vsize": max(vsize, 1),
        "confirmed": confirmed,
        "confirmations": 6 if confirmed else 0,
        "source_record": "live_blockchain_api",
    }


def fetch_live_transaction(txid: str) -> Optional[dict[str, Any]]:
    """Fetch live transaction from primary or alternate Bitcoin API."""
    if not txid or len(txid) != 64:
        return None

    res, source_endpoint = _request_with_failover(f"/tx/{txid}")
    if res and res.status_code == 200:
        try:
            data = res.json()
            normalized = normalize_esplora_tx(data)
            normalized["api_source"] = source_endpoint
            return normalized
        except Exception as err:
            logger.warning("Failed to parse JSON from %s/tx/%s: %s", source_endpoint, txid, err)

    return None


def fetch_address_transactions(address: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recent live transactions for an address with failover."""
    if not address or len(address) < 26:
        return []

    res, source_endpoint = _request_with_failover(f"/address/{address}/txs")
    if res and res.status_code == 200:
        try:
            raw_txs = res.json()
            normalized_list = []
            for tx in raw_txs[:limit]:
                norm = normalize_esplora_tx(tx)
                norm["api_source"] = source_endpoint
                normalized_list.append(norm)
            return normalized_list
        except Exception as err:
            logger.warning("Failed to parse transactions for %s: %s", address, err)

    return []


def fetch_fee_estimates() -> dict[str, Any]:
    """Fetch live mempool fee estimates (fastest, half-hour, hour)."""
    # Try esplora /fee-estimates
    res, ep = _request_with_failover("/fee-estimates")
    if res and res.status_code == 200:
        try:
            fees = res.json()
            # Returns { "1": 15.2, "2": 14.1, "6": 12.0 ... }
            return {
                "source": ep,
                "fastest_sat_vb": fees.get("1", 20.0),
                "half_hour_sat_vb": fees.get("3", 15.0),
                "hour_sat_vb": fees.get("6", 10.0),
                "economy_sat_vb": fees.get("144", 2.0),
            }
        except Exception:
            pass

    # Fallback to recommended fees endpoint on mempool.space
    try:
        with httpx.Client(timeout=4.0) as client:
            r = client.get("https://mempool.space/api/v1/fees/recommended")
            if r.status_code == 200:
                d = r.json()
                return {
                    "source": "https://mempool.space/api/v1/fees/recommended",
                    "fastest_sat_vb": d.get("fastestFee", 20),
                    "half_hour_sat_vb": d.get("halfHourFee", 15),
                    "hour_sat_vb": d.get("hourFee", 10),
                    "economy_sat_vb": d.get("economyFee", 2),
                }
    except Exception:
        pass

    # Safe deterministic defaults
    return {
        "source": "fallback_defaults",
        "fastest_sat_vb": 25.0,
        "half_hour_sat_vb": 18.0,
        "hour_sat_vb": 12.0,
        "economy_sat_vb": 2.0,
    }
