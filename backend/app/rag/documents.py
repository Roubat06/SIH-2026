from typing import List, Dict, Any

KNOWLEDGE_DOCUMENTS = [
    {
        'doc_id': 'KB-BTC-001',
        'title': 'UTXO Accounting Model & Forensic Implications',
        'category': 'Bitcoin Fundamentals',
        'content': """The Bitcoin blockchain operates on an Unspent Transaction Output (UTXO) model rather than an account-based model. Each transaction consumes one or more existing UTXOs as inputs and creates one or more new UTXOs as outputs. 

Key Investigative Realities:
1. Change Addresses: When an input exceeds the intended payment amount, a new change output is generated back to the sender. This means standard transactions typically have 2 outputs (Payment + Change).
2. Peeling Chains: A common pattern where a large fund is moved step-by-step, peeling off a small payment while transferring the remaining large balance to a fresh address.
3. Multi-Input Clustering Heuristic: When multiple inputs are spent together in a single transaction, common ownership is inferred (Common-Input Ownership Heuristic), except in CoinJoin mixers."""
    },
    {
        'doc_id': 'KB-TYP-002',
        'title': 'Peel Chains & Layering Obfuscation',
        'category': 'Typologies & Laundering Patterns',
        'content': """Peel chains are a classic transaction structuring method used to launder large amounts of cryptocurrency across sequential hops.

Characteristics:
- Asymmetric 2-output structure: One output carries >= 90% of the value (the unpeeled balance), while the second output carries a smaller amount to an exchange or service.
- Rapid succession: Transactions often occur in rapid succession across multiple blocks.
- Risk Interpretation: High transaction volume with constant peeling suggests programmatic movement or funds layering to obscure source of funds."""
    },
    {
        'doc_id': 'KB-TYP-003',
        'title': 'High Fan-Out vs Batch Payouts vs Mixers',
        'category': 'Typologies & Laundering Patterns',
        'content': """High Fan-Out occurs when a transaction has a disproportionately high number of outputs (e.g., >= 10 outputs).

Investigative Differentiation:
1. Legitimate Commercial Batching: Exchanges, mining pools, and payment processors batch hundreds of withdrawal payouts in a single transaction to minimize transaction fees.
2. Mixing / Obfuscation Dispersal: Illicit actors use fan-out to fragment stolen or flagged funds across disposable mule addresses.
3. CoinJoin Mixers: Characterized by multiple inputs from different parties and multiple outputs of EXACTLY equal value (e.g., 0.1 BTC each) to break deterministic transaction graphs."""
    },
    {
        'doc_id': 'KB-TYP-004',
        'title': 'Dusting Attacks and Tracking Markers',
        'category': 'Cyber Threat Intelligence',
        'content': """A Dusting Attack involves sending minuscule amounts of Bitcoin (typically < 1,000 satoshis, known as 'dust') to thousands of public addresses.

Forensic Significance:
- Purpose: Adversaries attempt to deanonymize wallet owners. When the unsuspecting victim spends this dust together with other unspent outputs, the attacker tracks the combined inputs using the multi-input ownership heuristic.
- Defense / Investigation: Investigators should identify unspent dust outputs and flag combined spends that tie previously unconnected clusters together."""
    },
    {
        'doc_id': 'KB-ML-005',
        'title': 'Isolation Forest Anomaly Detection Methodology',
        'category': 'ML & Detection Engine',
        'content': """Sentinel utilizes Isolation Forest as its primary unsupervised anomaly detection engine for high-dimensional Bitcoin transaction vectors.

Methodology:
- Tree Partitioning: Isolates anomalies by randomly selecting a feature and split value. Outlier transactions require significantly fewer random splits to isolate than normal baseline traffic.
- Score Normalization: Sentinel normalizes raw isolation scores into an in-dataset percentile rank (0-100).
- Review Thresholds: Percentiles >= 95.0 generate High Alerts; >= 98.0 generate Critical Alerts.
- Limitation: Unsupervised anomaly scores identify statistical rarity, NOT criminal guilt."""
    },
    {
        'doc_id': 'KB-INV-006',
        'title': 'Standard Operating Procedure (SOP) for Blockchain Investigations',
        'category': 'Investigation Procedures',
        'content': """When an alert is triggered in Sentinel, investigators should follow this standard 5-step SOP:
1. Triage Alert: Review anomaly percentile, triggered heuristic rules, and specific input/output values.
2. Graph Inspection: Open Graph Explorer to analyze 1-hop and 2-hop neighbor nodes (Address -> Transaction -> Address). Check if outputs converge or disperse.
3. Case Association: Assign the flagged transaction to an active investigation case or create a new case.
4. AI Security Analyst Inquiry: Consult AI Analyst with structured evidence for grounded hypotheses and recommended next steps.
5. Evidence Dossier Export: Add investigator notes, verify timeline chronology, and export the official signed investigation report."""
    }
]
