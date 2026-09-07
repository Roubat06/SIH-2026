#!/usr/bin/env python3
"""Generate a deterministic, synthetic Sentinel Tool import dataset."""

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

RECORDS = 240
FAN_OUT = {45: 16, 135: 14, 215: 18}
FAN_IN = {90: 14, 180: 12}
MISSING_FEE = {70, 170}
HIGH_FEE = {120}
HIGH_VALUE = {200}
BASE_TIME = datetime(2025, 1, 15, 8, 0, tzinfo=timezone.utc)
OUTPUT = Path(__file__).resolve().parents[1] / "samples" / "sentineltool-test-dataset.json"


def identifier(label: str) -> str:
    return sha256(f"sentineltool-dataset-v1:{label}".encode()).hexdigest()


def generate() -> dict:
    rows = []
    available = []
    observations = []
    signal_indexes = set(FAN_OUT) | set(FAN_IN) | MISSING_FEE | HIGH_FEE | HIGH_VALUE

    for index in range(RECORDS):
        txid = identifier(f"tx:{index}")
        if index in FAN_IN:
            input_count = min(FAN_IN[index], len(available))
            selected, available = available[:input_count], available[input_count:]
            budget = sum(item["value_sats"] for item in selected)
        elif index % 60 == 0 or index in HIGH_VALUE:
            selected = []
            budget = 2_100_000_000_000 if index in HIGH_VALUE else 8_000_000_000 + index * 10_000_000
        else:
            input_count = min(2 if index % 17 == 0 else 1, len(available))
            selected, available = available[:input_count], available[input_count:]
            budget = sum(item["value_sats"] for item in selected)

        inputs = [
            {
                "prev_txid": item["txid"],
                "prev_vout": item["index"],
                "sequence": 4294967293,
            }
            for item in selected
        ]
        output_count = FAN_OUT.get(index, 3 if index % 19 == 0 else 2)
        vsize = 100 + len(inputs) * 41 + output_count * 31
        actual_fee = 500_000 if index in HIGH_FEE else max(400, vsize * (2 + index % 5))
        spendable = max(output_count, budget - actual_fee)
        base_value, remainder = divmod(spendable, output_count)
        outputs = []
        for output_index in range(output_count):
            value = base_value + (1 if output_index < remainder else 0)
            output = {
                "index": output_index,
                "value_sats": value,
                "address": f"st-synthetic-{index:03d}-{output_index:02d}",
                "script_type": "p2wpkh" if output_index % 3 else "p2tr",
            }
            outputs.append(output)
            if value > 10_000:
                available.append({"txid": txid, **output})

        observed_at = BASE_TIME + timedelta(minutes=index * 6)
        confirmed = index < 215
        row = {
            "txid": txid,
            "observed_at": observed_at.isoformat(),
            "inputs": inputs,
            "outputs": outputs,
            "fee_sats": None if index in MISSING_FEE else actual_fee,
            "vsize": vsize,
            "size_bytes": vsize + 45,
            "weight": vsize * 4,
            "version": 2,
            "locktime": 0,
            "confirmed": confirmed,
            "confirmations": 6 if confirmed else 0,
            "block_height": 870_000 + index // 12 if confirmed else None,
            "block_hash": identifier(f"block:{index // 12}") if confirmed else None,
            "block_time": (observed_at + timedelta(minutes=9)).isoformat() if confirmed else None,
        }
        rows.append(row)

        if index % 12 == 0 or index in signal_indexes:
            observation_count = 3 if index in signal_indexes else 1
            test_ranges = ("192.0.2", "198.51.100", "203.0.113")
            for relay in range(observation_count):
                observations.append({
                    "txid": txid,
                    "observed_at": (observed_at + timedelta(seconds=relay * 2)).isoformat(),
                    "peer_ip": f"{test_ranges[relay % 3]}.{10 + (index + relay) % 190}",
                    "peer_port": 8333,
                    "sensor": f"synthetic-sensor-{relay + 1}",
                })

    return {
        "synthetic": True,
        "dataset_info": {
            "name": "Sentinel Tool mixed-traffic test dataset",
            "description": "Deterministic synthetic transactions for parser, graph, filter, timeline, and anomaly-alert testing. No record represents a real transaction or person.",
            "record_count": len(rows),
            "observation_count": len(observations),
            "expected_rule_signals": {
                "fan_out": [{"record": i + 1, "txid": rows[i]["txid"], "output_count": count} for i, count in sorted(FAN_OUT.items())],
                "fan_in": [{"record": i + 1, "txid": rows[i]["txid"], "input_count": count} for i, count in sorted(FAN_IN.items())],
            },
            "additional_model_outliers": {
                "missing_fee_records": [i + 1 for i in sorted(MISSING_FEE)],
                "high_fee_records": [i + 1 for i in sorted(HIGH_FEE)],
                "high_value_records": [i + 1 for i in sorted(HIGH_VALUE)],
            },
        },
        "transactions": rows,
        "observations": observations,
    }


def main() -> None:
    data = generate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {len(data['transactions'])} transactions and {len(data['observations'])} observations to {OUTPUT}")


if __name__ == "__main__":
    main()
