"""API Router for live Bitcoin blockchain data fetching and case import.

Includes failover between primary BITCOIN_API_URL and alternate free APIs.
"""
from __future__ import annotations
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .security import current_user, access, audit
from .db import database, now, public
from .analysis import analyze
from .bitcoin import (
    check_api_health,
    fetch_live_transaction,
    fetch_address_transactions,
    fetch_fee_estimates,
    get_bitcoin_endpoints,
)

router = APIRouter(prefix="/api/bitcoin", tags=["bitcoin"])


class LiveImportRequest(BaseModel):
    txid: Optional[str] = Field(default=None, min_length=64, max_length=64)
    address: Optional[str] = Field(default=None, min_length=26, max_length=90)


@router.get("/status")
def get_status(user=Depends(current_user)):
    """Check health and latency of primary and alternate free Bitcoin APIs."""
    return check_api_health()


@router.get("/fee-estimates")
def get_fee_estimates(user=Depends(current_user)):
    """Fetch live mempool fee estimates with automatic alternate failover."""
    return fetch_fee_estimates()


@router.get("/tx/{txid}")
def get_live_tx(txid: str, user=Depends(current_user)):
    """Fetch live transaction from blockchain with failover."""
    tx = fetch_live_transaction(txid)
    if not tx:
        raise HTTPException(
            404,
            detail=f"Transaction {txid} not found or Bitcoin APIs ({', '.join(get_bitcoin_endpoints())}) unreachable.",
        )
    return tx


@router.get("/address/{address}/txs")
def get_address_txs(address: str, user=Depends(current_user)):
    """Fetch recent live transactions for an address with failover."""
    txs = fetch_address_transactions(address)
    return {"address": address, "count": len(txs), "transactions": txs}


case_import_router = APIRouter(prefix="/api/cases", tags=["case-import"])


@case_import_router.post("/{case_id}/import-live")
def import_live_to_case(case_id: str, req: LiveImportRequest, user=Depends(current_user)):
    """Fetch live on-chain Bitcoin transaction(s) and import directly into case."""
    access(case_id, user)
    db = database()

    if not req.txid and not req.address:
        raise HTTPException(400, "Provide either a valid 'txid' or 'address' to fetch from Bitcoin blockchain.")

    fetched_txs = []
    source_label = ""

    if req.txid:
        tx = fetch_live_transaction(req.txid)
        if not tx:
            raise HTTPException(
                404,
                f"Could not retrieve transaction {req.txid} from primary or alternate Bitcoin APIs.",
            )
        fetched_txs.append(tx)
        source_label = f"Live TX: {req.txid[:12]}…"
    elif req.address:
        txs = fetch_address_transactions(req.address, limit=15)
        if not txs:
            raise HTTPException(
                404,
                f"No transactions found for address {req.address} via Bitcoin APIs.",
            )
        fetched_txs.extend(txs)
        source_label = f"Live Address: {req.address[:12]}…"

    dataset_id = secrets.token_hex(12)
    case_scope = {"case_id": case_id, "dataset_id": dataset_id}

    # Format into case transactions
    accepted = []
    for t in fetched_txs:
        t_copy = dict(t)
        t_copy["_id"] = secrets.token_hex(12)
        t_copy["case_id"] = case_id
        t_copy["dataset_id"] = dataset_id
        accepted.append(t_copy)

    # Insert transactions
    for t in accepted:
        # Avoid duplicate key if already in case
        existing = db.transactions.find_one({"case_id": case_id, "txid": t["txid"]})
        if not existing:
            db.transactions.insert_one(t)

    # Run AML & anomaly analysis
    alerts, features = analyze(accepted)
    for a in alerts:
        db.alerts.insert_one({"_id": secrets.token_hex(12), **case_scope, **a})
    for f in features:
        db.features.insert_one({"_id": secrets.token_hex(12), **case_scope, **f})

    # Record dataset
    db.datasets.insert_one({
        "_id": dataset_id,
        "case_id": case_id,
        "name": source_label,
        "sha256": secrets.token_hex(32),
        "status": "completed",
        "count": len(accepted),
        "progress": 100,
        "uploaded_by": user["_id"],
        "created_at": now(),
        "completed_at": now(),
        "source": "live_bitcoin_api",
        "api_endpoint": accepted[0].get("api_source", "live_api"),
    })

    audit(user["_id"], case_id, "live_bitcoin_data_imported", {
        "dataset_id": dataset_id,
        "count": len(accepted),
        "txid": req.txid,
        "address": req.address,
    })

    return {
        "status": "success",
        "dataset_id": dataset_id,
        "imported_count": len(accepted),
        "alerts_count": len(alerts),
        "transactions": [public(t) for t in accepted],
        "alerts": [public(a) for a in alerts],
    }
