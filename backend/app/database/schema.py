from .connection import db_session

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'ANALYST', 'VIEWER')),
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    txid TEXT PRIMARY KEY,
    block_hash TEXT,
    block_height INTEGER,
    block_time TIMESTAMP,
    observed_at TIMESTAMP,
    size_bytes INTEGER,
    vsize INTEGER,
    weight INTEGER,
    version INTEGER DEFAULT 2,
    locktime INTEGER DEFAULT 0,
    fee_sats INTEGER,
    fee_rate REAL,
    total_input_sats INTEGER DEFAULT 0,
    total_output_sats INTEGER DEFAULT 0,
    input_count INTEGER DEFAULT 0,
    output_count INTEGER DEFAULT 0,
    confirmed INTEGER DEFAULT 1,
    risk_score REAL DEFAULT 0.0,
    risk_level TEXT DEFAULT 'LOW' CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    anomaly_score REAL DEFAULT 0.0,
    anomaly_label INTEGER DEFAULT 1,
    is_flagged INTEGER DEFAULT 0,
    source TEXT DEFAULT 'seed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_inputs (
    id TEXT PRIMARY KEY,
    txid TEXT NOT NULL,
    prev_txid TEXT,
    prev_vout INTEGER,
    address TEXT,
    value_sats INTEGER DEFAULT 0,
    sequence INTEGER,
    script_type TEXT,
    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transaction_outputs (
    id TEXT PRIMARY KEY,
    txid TEXT NOT NULL,
    output_index INTEGER NOT NULL,
    address TEXT,
    value_sats INTEGER NOT NULL,
    script_type TEXT,
    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS addresses (
    address TEXT PRIMARY KEY,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    total_received_sats INTEGER DEFAULT 0,
    total_sent_sats INTEGER DEFAULT 0,
    tx_count INTEGER DEFAULT 0,
    risk_score REAL DEFAULT 0.0,
    risk_level TEXT DEFAULT 'LOW' CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    txid TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    risk_score REAL NOT NULL,
    anomaly_score REAL NOT NULL,
    detection_method TEXT NOT NULL,
    title TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT,
    status TEXT NOT NULL DEFAULT 'NEW' CHECK(status IN ('NEW', 'UNDER_REVIEW', 'ESCALATED', 'RESOLVED', 'FALSE_POSITIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detection_results (
    id TEXT PRIMARY KEY,
    txid TEXT NOT NULL,
    stage TEXT NOT NULL,
    detector TEXT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    feature TEXT,
    observed REAL,
    operator TEXT,
    threshold REAL,
    baseline REAL,
    unit TEXT,
    reason TEXT NOT NULL,
    severity TEXT NOT NULL,
    triggered INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'INVESTIGATING', 'ESCALATED', 'RESOLVED', 'CLOSED')),
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    lead_investigator_id TEXT,
    lead_investigator_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_transactions (
    case_id TEXT NOT NULL,
    txid TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(case_id, txid),
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY(txid) REFERENCES transactions(txid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investigation_events (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    txid TEXT,
    event_type TEXT NOT NULL,
    actor_id TEXT,
    actor_name TEXT,
    summary TEXT NOT NULL,
    details_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investigation_notes (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    author_id TEXT,
    author_name TEXT,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    actor_name TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    details_json TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    doc_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_runs (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_type TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    features_json TEXT,
    metrics_json TEXT,
    hyperparameters_json TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_risk ON transactions(risk_level, risk_score);
CREATE INDEX IF NOT EXISTS idx_tx_observed ON transactions(observed_at);
CREATE INDEX IF NOT EXISTS idx_tx_block_time ON transactions(block_time);
CREATE INDEX IF NOT EXISTS idx_tx_is_flagged ON transactions(is_flagged);
CREATE INDEX IF NOT EXISTS idx_inputs_txid ON transaction_inputs(txid);
CREATE INDEX IF NOT EXISTS idx_inputs_address ON transaction_inputs(address);
CREATE INDEX IF NOT EXISTS idx_inputs_prev_txid ON transaction_inputs(prev_txid);
CREATE INDEX IF NOT EXISTS idx_outputs_txid ON transaction_outputs(txid);
CREATE INDEX IF NOT EXISTS idx_outputs_address ON transaction_outputs(address);
CREATE INDEX IF NOT EXISTS idx_alerts_txid ON alerts(txid);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_detection_txid ON detection_results(txid);
CREATE INDEX IF NOT EXISTS idx_case_tx_case_id ON case_transactions(case_id);
CREATE INDEX IF NOT EXISTS idx_events_case_id ON investigation_events(case_id);
CREATE INDEX IF NOT EXISTS idx_events_txid ON investigation_events(txid);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
"""

def init_schema():
    with db_session() as conn:
        conn.executescript(SCHEMA_SQL)
