"""Lightweight, deterministic AML and financial transaction-monitoring indicators for Bitcoin.

All outputs are explainable risk indicators requiring human investigation.
No criminal attribution, credit-scoring, or financial forecasting.
"""
from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class AMLConfig:
    """Configurable thresholds and weights for deterministic Bitcoin AML risk analysis."""
    # Thresholds
    velocity_max_tx_per_window: int = 3
    velocity_window_minutes: int = 60
    volume_percentile: float = 95.0
    volume_min_sats: int = 500_000_000  # 5 BTC
    unusual_fee_ratio: float = 0.05       # Fee > 5% of transacted volume
    high_fee_rate_sat_vb: float = 120.0   # > 120 sat/vB
    fan_in_threshold: int = 10
    fan_out_threshold: int = 10
    address_reuse_threshold: int = 4
    peeling_chain_ratio: float = 4.0      # Primary output is >= 4x secondary output
    rapid_movement_minutes: int = 15      # Parent-to-child hop < 15 min

    # Weights for risk score aggregation (total 100 max)
    weight_velocity: float = 15.0
    weight_volume: float = 15.0
    weight_fee_ratio: float = 10.0
    weight_fan_in: float = 15.0
    weight_fan_out: float = 15.0
    weight_address_reuse: float = 10.0
    weight_peeling_chain: float = 15.0
    weight_rapid_movement: float = 15.0


def _parse_time(val: Any) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            cleaned = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def evaluate_aml_indicators(
    rows: list[dict[str, Any]],
    config: AMLConfig | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, float]]:
    """Compute deterministic AML behavioral indicators for a collection of transactions.

    Returns:
        detections_by_tx: txid -> list of detection dictionaries
        aml_scores_by_tx: txid -> composite AML risk score (0.0 - 100.0)
    """
    cfg = config or AMLConfig()
    eval_time = datetime.now(timezone.utc)

    # 1. Precompute dataset baselines
    totals = []
    for t in rows:
        val = sum(o["value_sats"] for o in t.get("outputs", []))
        totals.append(val)

    sorted_totals = sorted(totals) if totals else [0]
    p95_idx = int(len(sorted_totals) * (cfg.volume_percentile / 100.0))
    p95_idx = min(p95_idx, len(sorted_totals) - 1)
    dataset_volume_p95 = sorted_totals[p95_idx] if sorted_totals else 0
    median_volume = statistics.median(totals) if totals else 0

    median_in = statistics.median(len(t.get("inputs", [])) for t in rows) if rows else 0
    median_out = statistics.median(len(t.get("outputs", [])) for t in rows) if rows else 0

    # Index transactions by txid and previous outputs
    tx_by_id: dict[str, dict[str, Any]] = {t["txid"]: t for t in rows}
    tx_times: dict[str, datetime | None] = {}
    for t in rows:
        t_time = _parse_time(t.get("observed_at")) or _parse_time(t.get("block_time"))
        tx_times[t["txid"]] = t_time

    # Address index: address -> list of txids
    addr_to_txs: dict[str, set[str]] = {}
    for t in rows:
        txid = t["txid"]
        for o in t.get("outputs", []):
            addr = o.get("address")
            if addr:
                addr_to_txs.setdefault(addr, set()).add(txid)

    # Map output (prev_txid, prev_vout) -> child txid spending it
    spenders: dict[tuple[str, int], list[str]] = {}
    for t in rows:
        for inp in t.get("inputs", []):
            spenders.setdefault((inp["prev_txid"], inp["prev_vout"]), []).append(t["txid"])

    detections_by_tx: dict[str, list[dict[str, Any]]] = {t["txid"]: [] for t in rows}
    aml_scores_by_tx: dict[str, float] = {t["txid"]: 0.0 for t in rows}

    for t in rows:
        txid = t["txid"]
        signals: list[dict[str, Any]] = []
        inputs = t.get("inputs", [])
        outputs = t.get("outputs", [])
        total_out = sum(o["value_sats"] for o in outputs)
        fee_sats = t.get("fee_sats")
        vsize = t.get("vsize") or 1
        tx_time = tx_times[txid]

        score = 0.0

        # Indicator 1: Fan-Out Dispersion
        out_cnt = len(outputs)
        if out_cnt >= cfg.fan_out_threshold:
            score += cfg.weight_fan_out
            signals.append({
                "code": "fan_out",
                "stage": "rule_detection",
                "detector": "AML Fan-Out Rule",
                "title": "High output fan-out (batch/dispersion)",
                "feature": "output_count",
                "observed": out_cnt,
                "operator": ">=",
                "threshold": cfg.fan_out_threshold,
                "baseline": median_out,
                "unit": "outputs",
                "detected_at": eval_time,
                "weight": cfg.weight_fan_out,
                "reason": (
                    f"Transaction dispatches funds across {out_cnt} outputs "
                    f"(configured threshold: {cfg.fan_out_threshold}; dataset median: {median_out:g}). "
                    f"Common in payment batching, dusting, or layered fund distribution."
                ),
            })

        # Indicator 2: Fan-In Consolidation
        in_cnt = len(inputs)
        if in_cnt >= cfg.fan_in_threshold:
            score += cfg.weight_fan_in
            signals.append({
                "code": "fan_in",
                "stage": "rule_detection",
                "detector": "AML Fan-In Rule",
                "title": "High input fan-in (UTXO consolidation)",
                "feature": "input_count",
                "observed": in_cnt,
                "operator": ">=",
                "threshold": cfg.fan_in_threshold,
                "baseline": median_in,
                "unit": "inputs",
                "detected_at": eval_time,
                "weight": cfg.weight_fan_in,
                "reason": (
                    f"Transaction consolidates {in_cnt} distinct input UTXOs "
                    f"(configured threshold: {cfg.fan_in_threshold}; dataset median: {median_in:g}). "
                    f"Common in exchange sweeping, wallet maintenance, or structured aggregation."
                ),
            })

        # Indicator 3: Transaction Volume Anomaly
        effective_vol_thresh = max(cfg.volume_min_sats, dataset_volume_p95)
        if total_out >= effective_vol_thresh and total_out > 0:
            score += cfg.weight_volume
            signals.append({
                "code": "aml_volume",
                "stage": "rule_detection",
                "detector": "AML High Volume Monitor",
                "title": "Outlier transaction output volume",
                "feature": "total_output_sats",
                "observed": total_out,
                "operator": ">=",
                "threshold": effective_vol_thresh,
                "baseline": median_volume,
                "unit": "sats",
                "detected_at": eval_time,
                "weight": cfg.weight_volume,
                "reason": (
                    f"Transaction output volume ({total_out:,} satoshis / {total_out / 1e8:.4g} BTC) "
                    f"exceeds the 95th percentile volume threshold ({effective_vol_thresh:,} satoshis). "
                    f"Represents a high-value value transfer requiring provenance review."
                ),
            })

        # Indicator 4: Unusual Fee / Value Ratio
        if fee_sats is not None and total_out > 0:
            fee_ratio = fee_sats / total_out
            fee_rate = fee_sats / vsize if vsize > 0 else 0
            if fee_ratio >= cfg.unusual_fee_ratio or fee_rate >= cfg.high_fee_rate_sat_vb:
                score += cfg.weight_fee_ratio
                observed_val = round(fee_ratio * 100, 2)
                signals.append({
                    "code": "aml_fee_ratio",
                    "stage": "rule_detection",
                    "detector": "AML Fee/Value Ratio Monitor",
                    "title": "Unusual fee-to-value ratio or extreme fee rate",
                    "feature": "fee_value_ratio_pct",
                    "observed": observed_val,
                    "operator": ">=",
                    "threshold": round(cfg.unusual_fee_ratio * 100, 2),
                    "baseline": None,
                    "unit": "%",
                    "detected_at": eval_time,
                    "weight": cfg.weight_fee_ratio,
                    "reason": (
                        f"Mining fee ({fee_sats:,} satoshis at {fee_rate:.1f} sat/vB) represents "
                        f"{observed_val}% of total transacted output value. "
                        f"Disproportionately high fee rates may signal high-urgency laundering, "
                        f"dust transmission, or fee-draining activity."
                    ),
                })

        # Indicator 5: Repeated Address Interactions / Address Reuse
        current_addrs = {o.get("address") for o in outputs if o.get("address")}
        max_reuse = max((len(addr_to_txs.get(a, [])) for a in current_addrs), default=0)
        if max_reuse >= cfg.address_reuse_threshold:
            score += cfg.weight_address_reuse
            signals.append({
                "code": "aml_address_reuse",
                "stage": "rule_detection",
                "detector": "AML Address Reuse Monitor",
                "title": "Repeated address interactions across dataset",
                "feature": "max_address_frequency",
                "observed": max_reuse,
                "operator": ">=",
                "threshold": cfg.address_reuse_threshold,
                "baseline": 1,
                "unit": "transactions",
                "detected_at": eval_time,
                "weight": cfg.weight_address_reuse,
                "reason": (
                    f"Address associated with this transaction appears in {max_reuse} distinct "
                    f"transactions in the imported dataset (threshold: {cfg.address_reuse_threshold}). "
                    f"Reduces pseudonymity and indicates shared infrastructure or repeat counterparties."
                ),
            })

        # Indicator 6: Peeling-Chain-Like Pattern
        # Pattern: 1 input -> 2 outputs, where one output is smaller payment and one larger output
        # is subsequent peel change, or vice versa with split ratio >= peeling_chain_ratio.
        if len(inputs) == 1 and len(outputs) == 2:
            v0, v1 = outputs[0]["value_sats"], outputs[1]["value_sats"]
            min_v, max_v = min(v0, v1), max(v0, v1)
            ratio = max_v / min_v if min_v > 0 else 0
            # Check if one of the outputs is spent by another 1-input or 2-output transaction
            is_peel = ratio >= cfg.peeling_chain_ratio
            if is_peel:
                score += cfg.weight_peeling_chain
                signals.append({
                    "code": "aml_peeling_chain",
                    "stage": "rule_detection",
                    "detector": "AML Peeling Chain Heuristic",
                    "title": "Peeling-chain behavioral pattern",
                    "feature": "output_asymmetry_ratio",
                    "observed": round(ratio, 1),
                    "operator": ">=",
                    "threshold": cfg.peeling_chain_ratio,
                    "baseline": 1.0,
                    "unit": "ratio",
                    "detected_at": eval_time,
                    "weight": cfg.weight_peeling_chain,
                    "reason": (
                        f"Transaction exhibits asymmetric 1-in-2-out peeling structure "
                        f"(ratio: {ratio:.1f}x between larger and smaller outputs). "
                        f"Characteristic of automated payment sweeps, mixers, or progressive peeling chains."
                    ),
                })

        # Indicator 7: Transaction Velocity (Cluster Burst)
        if tx_time:
            # Count transactions in case within rolling window associated with any common address
            shared_txids: set[str] = set()
            for a in current_addrs:
                shared_txids.update(addr_to_txs.get(a, []))
            
            # Count how many of these shared txs occurred within window
            window_delta = timedelta(minutes=cfg.velocity_window_minutes)
            burst_count = 0
            for peer_id in shared_txids:
                peer_time = tx_times.get(peer_id)
                if peer_time and abs(peer_time - tx_time) <= window_delta:
                    burst_count += 1

            if burst_count >= cfg.velocity_max_tx_per_window:
                score += cfg.weight_velocity
                signals.append({
                    "code": "aml_velocity",
                    "stage": "rule_detection",
                    "detector": "AML Velocity Monitor",
                    "title": "High transaction velocity in localized window",
                    "feature": "transactions_in_window",
                    "observed": burst_count,
                    "operator": ">=",
                    "threshold": cfg.velocity_max_tx_per_window,
                    "baseline": 1,
                    "unit": "txs/window",
                    "detected_at": eval_time,
                    "weight": cfg.weight_velocity,
                    "reason": (
                        f"Detected {burst_count} correlated transactions within a "
                        f"{cfg.velocity_window_minutes}-minute temporal window "
                        f"(threshold: {cfg.velocity_max_tx_per_window}). "
                        f"Rapid sequence transfers may suggest automated fund movement or structuring."
                    ),
                })

        # Indicator 8: Rapid Movement Across Connected Addresses
        if tx_time and inputs:
            parent_times = []
            for inp in inputs:
                parent = tx_by_id.get(inp["prev_txid"])
                if parent:
                    p_time = tx_times.get(parent["txid"])
                    if p_time:
                        parent_times.append(p_time)
            if parent_times:
                min_delta_sec = min((tx_time - pt).total_seconds() for pt in parent_times if tx_time >= pt)
                min_delta_min = min_delta_sec / 60.0 if min_delta_sec is not None else None
                if min_delta_min is not None and 0 <= min_delta_min <= cfg.rapid_movement_minutes:
                    score += cfg.weight_rapid_movement
                    signals.append({
                        "code": "aml_rapid_movement",
                        "stage": "rule_detection",
                        "detector": "AML Hop Velocity Monitor",
                        "title": "Rapid fund movement across connected addresses",
                        "feature": "hop_latency_minutes",
                        "observed": round(min_delta_min, 1),
                        "operator": "<=",
                        "threshold": cfg.rapid_movement_minutes,
                        "baseline": 60,
                        "unit": "minutes",
                        "detected_at": eval_time,
                        "weight": cfg.weight_rapid_movement,
                        "reason": (
                            f"Funds were spent within {min_delta_min:.1f} minutes of receipt from parent transaction "
                            f"(threshold: <= {cfg.rapid_movement_minutes} minutes). "
                            f"Minimal dwell time indicates pass-through intermediary routing."
                        ),
                    })

        detections_by_tx[txid] = signals
        aml_scores_by_tx[txid] = min(100.0, round(score, 1))

    return detections_by_tx, aml_scores_by_tx
