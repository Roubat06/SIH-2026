import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np

FEATURE_NAMES = [
    'input_count',
    'output_count',
    'total_output_sats',
    'log_output_sats',
    'fee_sats',
    'fee_rate',
    'vsize',
    'largest_output_share',
    'input_output_ratio',
    'value_per_input',
    'value_per_output',
    'fee_to_value_ratio',
    'dust_output_count',
    'equal_output_pairs'
]

def extract_features_from_tx(tx: Dict[str, Any]) -> List[float]:
    inputs = tx.get('inputs', [])
    outputs = tx.get('outputs', [])
    
    in_count = len(inputs) if inputs else int(tx.get('input_count', 0))
    out_count = len(outputs) if outputs else int(tx.get('output_count', 0))
    
    out_values = [o.get('value_sats', 0) for o in outputs] if outputs else []
    total_out = sum(out_values) if out_values else int(tx.get('total_output_sats', 0))
    
    in_values = [i.get('value_sats', 0) for i in inputs] if inputs else []
    total_in = sum(in_values) if in_values else int(tx.get('total_input_sats', 0))
    
    fee = int(tx.get('fee_sats') or 0)
    vsize = int(tx.get('vsize') or 140)
    fee_rate = float(tx.get('fee_rate') or (fee / max(vsize, 1)))
    
    max_out = max(out_values) if out_values else total_out
    largest_out_share = (max_out / total_out) if total_out > 0 else 0.0
    
    io_ratio = (in_count / max(out_count, 1))
    val_per_in = (total_in / max(in_count, 1)) if in_count > 0 else 0.0
    val_per_out = (total_out / max(out_count, 1)) if out_count > 0 else 0.0
    fee_val_ratio = (fee / max(total_out, 1)) if total_out > 0 else 0.0
    
    dust_count = sum(1 for v in out_values if 0 < v <= 1000)
    
    val_counts = {}
    for v in out_values:
        val_counts[v] = val_counts.get(v, 0) + 1
    equal_pairs = sum(c * (c - 1) // 2 for c in val_counts.values() if c > 1)
    
    log_out = math.log1p(total_out)
    
    return [
        float(in_count),
        float(out_count),
        float(total_out),
        float(log_out),
        float(fee),
        float(fee_rate),
        float(vsize),
        float(largest_out_share),
        float(io_ratio),
        float(val_per_in),
        float(val_per_out),
        float(fee_val_ratio),
        float(dust_count),
        float(equal_pairs)
    ]

def build_feature_matrix(tx_list: List[Dict[str, Any]]) -> np.ndarray:
    rows = [extract_features_from_tx(tx) for tx in tx_list]
    return np.array(rows, dtype=np.float64)
