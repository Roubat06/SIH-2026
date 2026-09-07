import training from "./demo-transactions.json";

export type User = {
  id: string;
  name: string;
  email: string;
  role: "ADMIN" | "ANALYST" | "VIEWER";
};

export type TxInput = {
  prev_txid?: string | null;
  prev_vout?: number | null;
  address?: string | null;
  value_sats: number;
  sequence?: number | null;
  script_type?: string | null;
};

export type TxOutput = {
  output_index: number;
  address?: string | null;
  value_sats: number;
  script_type?: string | null;
};

export type Detection = {
  id?: string;
  code: string;
  stage: string;
  detector: string;
  title: string;
  feature?: string;
  observed?: number;
  operator?: string;
  threshold?: number;
  baseline?: number | null;
  unit?: string;
  reason: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  created_at?: string;
};

export type Tx = {
  txid: string;
  block_hash?: string | null;
  block_height?: number | null;
  block_time?: string | null;
  observed_at?: string | null;
  size_bytes?: number | null;
  vsize?: number | null;
  weight?: number | null;
  fee_sats?: number | null;
  fee_rate?: number | null;
  total_input_sats: number;
  total_output_sats: number;
  input_count: number;
  output_count: number;
  confirmed: boolean;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  anomaly_score: number;
  anomaly_label: number;
  is_flagged: boolean;
  source: string;
  inputs?: TxInput[];
  outputs?: TxOutput[];
  detections?: Detection[];
  alerts?: Alert[];
  cases?: Case[];
};

export type Alert = {
  id: string;
  txid: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  anomaly_score: number;
  detection_method: string;
  title: string;
  reason: string;
  evidence_json?: string;
  status: "NEW" | "UNDER_REVIEW" | "ESCALATED" | "RESOLVED" | "FALSE_POSITIVE";
  created_at: string;
  updated_at?: string;
  total_output_sats?: number;
  input_count?: number;
  output_count?: number;
  fee_rate?: number;
  observed_at?: string;
  transaction?: Tx;
  detections?: Detection[];
};

export type Case = {
  id: string;
  title: string;
  description?: string;
  status: "OPEN" | "INVESTIGATING" | "ESCALATED" | "RESOLVED" | "CLOSED";
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  lead_investigator_id?: string;
  lead_investigator_name?: string;
  transaction_count?: number;
  created_at?: string;
  updated_at?: string;
  transactions?: Tx[];
  timeline?: InvestigationEvent[];
  notes?: InvestigationNote[];
};

export type InvestigationEvent = {
  id: string;
  case_id?: string;
  txid?: string;
  event_type: string;
  actor_id?: string;
  actor_name?: string;
  summary: string;
  details_json?: string;
  created_at: string;
};

export type InvestigationNote = {
  id: string;
  case_id: string;
  author_id?: string;
  author_name?: string;
  note: string;
  created_at: string;
};

export type AuditLog = {
  id: string;
  actor_id?: string;
  actor_name?: string;
  action: string;
  target_type?: string;
  target_id?: string;
  details_json?: string;
  ip_address?: string;
  created_at: string;
};

export type GraphElement = {
  data: {
    id: string;
    label: string;
    type?: "transaction" | "address";
    source?: string;
    target?: string;
    risk_score?: number;
    risk_level?: string;
    total_sats?: number;
    value_sats?: number;
    is_target?: boolean;
    is_input?: boolean;
    is_output?: boolean;
  };
};

export type GraphResponse = {
  target_txid: string;
  node_count: number;
  edge_count: number;
  elements: {
    nodes: GraphElement[];
    edges: GraphElement[];
  };
  disclaimer: string;
};

export type DashboardSummary = {
  kpis: {
    monitored_transactions: number;
    active_alerts: number;
    high_risk_transactions: number;
    open_cases: number;
    anomalies_detected: number;
  };
  risk_distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
  alert_severity_distribution: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
  traffic_series: {
    hour_bucket: string;
    tx_count: number;
    total_volume_sats: number;
    avg_risk: number;
  }[];
  recent_alerts: Alert[];
  recent_cases: Case[];
  ingestion_status: {
    latest_block: number;
    block_hash: string;
    status: string;
    source: string;
    total_stored: number;
    last_sync: string;
  };
};

export type AIAnalysisResponse = {
  summary: string;
  evidence: string[];
  why_it_matters: string;
  recommended_steps: string[];
  limitations: string;
  facts: string[];
  model_indications: string[];
  suggestions: string[];
  model_used: string;
  rag_sources: string[];
};

export const short = (s: string, n = 8) =>
  s && s.length > n * 2 ? `${s.slice(0, n)}…${s.slice(-n)}` : s || "";

export const btc = (n: number) =>
  ((n || 0) / 1e8).toLocaleString("en-US", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 6,
  });

export const sats = (n: number) => (n || 0).toLocaleString("en-US");

export const timeAgo = (dateStr?: string) => {
  if (!dateStr) return "N/A";
  const d = new Date(dateStr);
  const now = new Date();
  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diffSec < 60) return `${Math.max(1, diffSec)}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
};

// API Helper
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("sentinel_jwt_token");
  const headers: Record<string, string> = {
    "X-Sentinel-Request": "1",
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(path.startsWith("/api") ? path : `/api${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const err = await response.json();
      errorDetail = err.detail || err.message || errorDetail;
    } catch {}
    throw new Error(errorDetail);
  }

  if (response.status === 204) return null as T;
  return response.json();
}

export const api = {
  getDashboard: () => apiFetch<DashboardSummary>("/api/dashboard"),
  getTransactions: (params: string = "") => apiFetch<{ items: Tx[]; total: number }>(`/api/transactions?${params}`),
  getTransaction: (txid: string) => apiFetch<Tx>(`/api/transactions/${txid}`),
  getAlerts: (params: string = "") => apiFetch<{ items: Alert[]; total: number }>(`/api/alerts?${params}`),
  getAlert: (id: string) => apiFetch<Alert>(`/api/alerts/${id}`),
  updateAlertStatus: (id: string, status: string, note?: string) =>
    apiFetch<{ message: string }>(`/api/alerts/${id}/status`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    }),
  getCases: (status?: string) => apiFetch<Case[]>(`/api/cases${status ? `?status=${status}` : ""}`),
  createCase: (data: { title: string; description?: string; priority?: string; txids?: string[] }) =>
    apiFetch<Case>("/api/cases", { method: "POST", body: JSON.stringify(data) }),
  getCase: (id: string) => apiFetch<Case>(`/api/cases/${id}`),
  addCaseNote: (caseId: string, note: string) =>
    apiFetch<{ message: string }>(`/api/cases/${caseId}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  attachTxToCase: (caseId: string, txid: string) =>
    apiFetch<{ message: string }>(`/api/cases/${caseId}/transactions/${txid}`, { method: "POST" }),
  getGraph: (txid: string) => apiFetch<GraphResponse>(`/api/graph/${txid}`),
  getBitcoinStatus: () => apiFetch<any>("/api/bitcoin/status"),
  syncBitcoin: (count = 15, useLiveApi = false) =>
    apiFetch<{ status: string; transactions_processed: number; alerts_generated: number }>(
      "/api/bitcoin/sync",
      { method: "POST", body: JSON.stringify({ count, use_live_api: useLiveApi }) }
    ),
  getModelStatus: () => apiFetch<any>("/api/models/status"),
  getModelEvaluation: () => apiFetch<any>("/api/models/evaluation"),
  searchKnowledge: (query: string, limit = 4) =>
    apiFetch<{ results: any[]; total_matches: number }>("/api/rag/search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    }),
  queryAIAnalyst: (prompt: string, txid?: string, caseId?: string, includeRag = true) =>
    apiFetch<AIAnalysisResponse>("/api/ai/analyze", {
      method: "POST",
      body: JSON.stringify({ prompt, txid, case_id: caseId, include_rag: includeRag }),
    }),
  generateReport: (caseId: string) =>
    apiFetch<any>(`/api/reports/${caseId}`, { method: "POST" }),
  getAuditLogs: (limit = 50) => apiFetch<{ items: AuditLog[]; total: number }>(`/api/audit?limit=${limit}`),
  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => apiFetch<User>("/api/auth/me"),
};

export function downloadReportJSON(data: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

