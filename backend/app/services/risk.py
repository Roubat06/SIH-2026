from typing import Dict, Any, List, Tuple

def compute_risk_score(tx: Dict[str, Any], triggered_rules: List[Dict[str, Any]], anomaly_score: float) -> Tuple[float, str, List[str]]:
    factors = []
    base_score = 0.0
    
    # 1. Anomaly score contribution (up to 40 points)
    if anomaly_score >= 98.0:
        base_score += 40.0
        factors.append(f'Severe multivariate statistical anomaly (Percentile: {anomaly_score:.1f}/100)')
    elif anomaly_score >= 95.0:
        base_score += 28.0
        factors.append(f'Elevated multivariate statistical anomaly (Percentile: {anomaly_score:.1f}/100)')
    elif anomaly_score >= 90.0:
        base_score += 15.0
        factors.append(f'Moderate anomaly score (Percentile: {anomaly_score:.1f}/100)')
    else:
        base_score += (anomaly_score / 100.0) * 10.0
        
    # 2. Rule severity contributions (up to 60 points)
    for rule in triggered_rules:
        sev = rule.get('severity', 'LOW')
        title = rule.get('title', 'Rule triggered')
        reason = rule.get('reason', '')
        
        if sev == 'HIGH' or sev == 'CRITICAL':
            base_score += 22.0
            factors.append(f'High-Severity Detection: {title} ({reason})')
        elif sev == 'MEDIUM':
            base_score += 12.0
            factors.append(f'Medium-Severity Detection: {title} ({reason})')
        else:
            base_score += 5.0
            factors.append(f'Low-Severity Detection: {title}')
            
    # Normalize to 0-100
    final_score = round(min(100.0, max(0.0, base_score)), 1)
    
    if final_score >= 80.0:
        level = 'CRITICAL'
    elif final_score >= 60.0:
        level = 'HIGH'
    elif final_score >= 35.0:
        level = 'MEDIUM'
    else:
        level = 'LOW'
        
    if not factors:
        factors.append('Baseline transaction parameters within normal bounds.')
        
    return final_score, level, factors
