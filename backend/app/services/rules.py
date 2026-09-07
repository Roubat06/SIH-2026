from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

RULES_DEFINITIONS = [
    {
        'id': 'R01',
        'code': 'high_transaction_value',
        'title': 'High Transaction Value (>= 5 BTC)',
        'severity': 'MEDIUM',
        'description': 'Flags transactions moving 500,000,000 or more Satoshis in a single transfer.'
    },
    {
        'id': 'R02',
        'code': 'high_fan_out',
        'title': 'High Output Fan-Out (>= 10 Outputs)',
        'severity': 'HIGH',
        'description': 'Unusual batch payout or mixing distribution pattern with 10 or more output UTXOs.'
    },
    {
        'id': 'R03',
        'code': 'high_consolidation_fan_in',
        'title': 'High Input Consolidation (>= 10 Inputs)',
        'severity': 'MEDIUM',
        'description': 'Consolidation of 10 or more fragmented UTXOs into fewer outputs.'
    },
    {
        'id': 'R04',
        'code': 'rapid_peeling_chain',
        'title': 'Peel Chain Structuring Signature',
        'severity': 'HIGH',
        'description': 'Classic peel chain pattern: 2 outputs where one carries >= 92% of the value and the other carries change.'
    },
    {
        'id': 'R05',
        'code': 'abnormal_fee_rate',
        'title': 'Abnormal Fee Rate (>= 150 sat/vB or 0 fee)',
        'severity': 'MEDIUM',
        'description': 'Fee rate deviates significantly from normal network conditions (urgent propagation or zero fee).'
    },
    {
        'id': 'R06',
        'code': 'dust_attack_pattern',
        'title': 'Dusting Attack / Micro-Output Pattern',
        'severity': 'HIGH',
        'description': 'Multiple micro-outputs (<= 1,000 sats) indicating potential wallet de-anonymization / dust tracking.'
    },
    {
        'id': 'R07',
        'code': 'equal_output_split',
        'title': 'Equal-Value Output Split (CoinJoin / Mixing)',
        'severity': 'HIGH',
        'description': 'Multiple outputs carrying identical satoshi denominations, characteristic of mixer obfuscation.'
    },
    {
        'id': 'R08',
        'code': 'highly_connected_entity',
        'title': 'High Graph Connectivity / Centrality',
        'severity': 'HIGH',
        'description': 'Transaction interacts with addresses having elevated degree centrality and repeated hops.'
    }
]

def evaluate_rules(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    triggered = []
    now = datetime.now(timezone.utc).isoformat()
    
    inputs = tx.get('inputs', [])
    outputs = tx.get('outputs', [])
    in_count = len(inputs) if inputs else int(tx.get('input_count', 0))
    out_count = len(outputs) if outputs else int(tx.get('output_count', 0))
    
    out_values = [o.get('value_sats', 0) for o in outputs] if outputs else []
    total_out = sum(out_values) if out_values else int(tx.get('total_output_sats', 0))
    
    fee = int(tx.get('fee_sats') or 0)
    vsize = int(tx.get('vsize') or 140)
    fee_rate = float(tx.get('fee_rate') or (fee / max(vsize, 1)))
    
    # R01: High Value
    if total_out >= 500_000_000:
        triggered.append({
            'code': 'high_transaction_value',
            'stage': 'rule_detection',
            'detector': 'Rule Engine [R01]',
            'title': 'High Transaction Value',
            'feature': 'total_output_sats',
            'observed': float(total_out),
            'operator': '>=',
            'threshold': 500_000_000.0,
            'baseline': 25_000_000.0,
            'unit': 'satoshis',
            'reason': f'Transfers {total_out / 100_000_000:.3f} BTC ({total_out:,} sats), exceeding the 5.0 BTC security threshold.',
            'severity': 'MEDIUM'
        })
        
    # R02: High Fan-Out
    if out_count >= 10:
        triggered.append({
            'code': 'high_fan_out',
            'stage': 'rule_detection',
            'detector': 'Rule Engine [R02]',
            'title': 'Unusual Output Fan-Out',
            'feature': 'output_count',
            'observed': float(out_count),
            'operator': '>=',
            'threshold': 10.0,
            'baseline': 2.0,
            'unit': 'outputs',
            'reason': f'{out_count} output destinations detected, matching batch payout or funds dispersion patterns.',
            'severity': 'HIGH'
        })
        
    # R03: High Fan-In
    if in_count >= 10:
        triggered.append({
            'code': 'high_consolidation_fan_in',
            'stage': 'rule_detection',
            'detector': 'Rule Engine [R03]',
            'title': 'High Input Consolidation',
            'feature': 'input_count',
            'observed': float(in_count),
            'operator': '>=',
            'threshold': 10.0,
            'baseline': 1.0,
            'unit': 'inputs',
            'reason': f'{in_count} UTXOs consolidated in a single transaction, exceeding standard wallet behavior baseline.',
            'severity': 'MEDIUM'
        })
        
    # R04: Peel Chain Structuring
    if out_count == 2 and total_out > 50_000_000 and len(out_values) == 2:
        max_val = max(out_values)
        share = max_val / total_out
        if share >= 0.92:
            triggered.append({
                'code': 'rapid_peeling_chain',
                'stage': 'rule_detection',
                'detector': 'Rule Engine [R04]',
                'title': 'Peel Chain Structuring Signature',
                'feature': 'largest_output_share',
                'observed': round(share * 100, 1),
                'operator': '>=',
                'threshold': 92.0,
                'baseline': 50.0,
                'unit': 'percent',
                'reason': f'Asymmetric 2-output split where {share*100:.1f}% remains in peel output and {(1-share)*100:.1f}% is peeled as change.',
                'severity': 'HIGH'
            })
            
    # R05: Abnormal Fee Rate
    if fee_rate >= 150.0 or (fee == 0 and total_out > 10_000_000):
        triggered.append({
            'code': 'abnormal_fee_rate',
            'stage': 'rule_detection',
            'detector': 'Rule Engine [R05]',
            'title': 'Abnormal Fee Rate',
            'feature': 'fee_rate',
            'observed': round(fee_rate, 2),
            'operator': '>=',
            'threshold': 150.0,
            'baseline': 18.0,
            'unit': 'sat/vB',
            'reason': f'Transaction fee rate of {fee_rate:.1f} sat/vB indicates unusual urgency or anomalous fee structure.',
            'severity': 'MEDIUM'
        })
        
    # R06: Dusting Attack
    if out_values:
        dust_outs = [v for v in out_values if 0 < v <= 1000]
        if len(dust_outs) >= 2 or (len(dust_outs) >= 1 and out_count > 3):
            triggered.append({
                'code': 'dust_attack_pattern',
                'stage': 'rule_detection',
                'detector': 'Rule Engine [R06]',
                'title': 'Dusting / Micro-Output Pattern',
                'feature': 'dust_output_count',
                'observed': float(len(dust_outs)),
                'operator': '>=',
                'threshold': 2.0,
                'baseline': 0.0,
                'unit': 'micro-outputs',
                'reason': f'{len(dust_outs)} dust output(s) (<= 1,000 sats) detected, matching potential wallet tracking markers.',
                'severity': 'HIGH'
            })
            
    # R07: Equal Output Split
    if out_count >= 3 and out_values:
        val_counts = {}
        for v in out_values:
            val_counts[v] = val_counts.get(v, 0) + 1
        max_equal = max(val_counts.values()) if val_counts else 0
        if max_equal >= 3:
            triggered.append({
                'code': 'equal_output_split',
                'stage': 'rule_detection',
                'detector': 'Rule Engine [R07]',
                'title': 'Equal-Value Output Split (CoinJoin Pattern)',
                'feature': 'equal_output_count',
                'observed': float(max_equal),
                'operator': '>=',
                'threshold': 3.0,
                'baseline': 1.0,
                'unit': 'equal_outputs',
                'reason': f'{max_equal} outputs share identical values, matching cryptographic mixer/CoinJoin obfuscation.',
                'severity': 'HIGH'
            })
            
    # R08: High Degree Connectivity
    if in_count >= 5 and out_count >= 5:
        triggered.append({
            'code': 'highly_connected_entity',
            'stage': 'rule_detection',
            'detector': 'Rule Engine [R08]',
            'title': 'High Graph Connectivity Nexus',
            'feature': 'connectivity_degree',
            'observed': float(in_count + out_count),
            'operator': '>=',
            'threshold': 10.0,
            'baseline': 3.0,
            'unit': 'degree',
            'reason': f'Combined degree of {in_count + out_count} connects multiple upstream and downstream clusters.',
            'severity': 'HIGH'
        })
        
    return triggered
