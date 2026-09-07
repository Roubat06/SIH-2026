import React, { useEffect, useState, useRef } from "react";
import {
  LayoutDashboard,
  Activity,
  ShieldAlert,
  Briefcase,
  GitBranch,
  Bot,
  BookOpen,
  FileCheck,
  ClipboardList,
  Sliders,
  Search,
  Filter,
  RefreshCw,
  Plus,
  ArrowUpRight,
  ExternalLink,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  Download,
  Eye,
  LogOut,
  UserCheck,
  Send,
  HelpCircle,
  Database,
  Layers,
  ChevronDown,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import Graph from "./Graph";
import {
  api,
  btc,
  sats,
  short,
  timeAgo,
  downloadReportJSON,
  type User,
  type DashboardSummary,
  type Tx,
  type Alert,
  type Case,
  type GraphResponse,
  type AIAnalysisResponse,
  type AuditLog,
} from "./data";

type NavTab =
  | "dashboard"
  | "transactions"
  | "alerts"
  | "cases"
  | "graph"
  | "ai_analyst"
  | "knowledge_base"
  | "reports"
  | "audit_logs"
  | "model_eval";

const NAV_ITEMS: { id: NavTab; label: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "transactions", label: "Transactions", icon: Activity },
  { id: "alerts", label: "Alert Queue", icon: ShieldAlert },
  { id: "cases", label: "Investigations", icon: Briefcase },
  { id: "graph", label: "Graph Explorer", icon: GitBranch },
  { id: "ai_analyst", label: "AI Analyst", icon: Bot },
  { id: "knowledge_base", label: "Forensic RAG", icon: BookOpen },
  { id: "reports", label: "Reports", icon: FileCheck },
  { id: "audit_logs", label: "Audit Logs", icon: ClipboardList },
  { id: "model_eval", label: "ML & Engine", icon: Sliders },
];

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#38bdf8",
  MEDIUM: "#e8b36a",
  HIGH: "#fb923c",
  CRITICAL: "#f87171",
};

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [user, setUser] = useState<User | null>(null);
  const [authEmail, setAuthEmail] = useState("analyst@sentinel.sec");
  const [authPassword, setAuthPassword] = useState("analyst123");
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authError, setAuthError] = useState("");

  // Notification / Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Global Contexts
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [syncingBitcoin, setSyncingBitcoin] = useState(false);

  // Transactions Tab
  const [transactions, setTransactions] = useState<Tx[]>([]);
  const [totalTxCount, setTotalTxCount] = useState(0);
  const [txSearch, setTxSearch] = useState("");
  const [txRiskFilter, setTxRiskFilter] = useState("");
  const [selectedTx, setSelectedTx] = useState<Tx | null>(null);
  const [loadingTx, setLoadingTx] = useState(false);

  // Alerts Tab
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [totalAlertsCount, setTotalAlertsCount] = useState(0);
  const [alertSeverityFilter, setAlertSeverityFilter] = useState("");
  const [alertStatusFilter, setAlertStatusFilter] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Cases Tab
  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [newCaseDesc, setNewCaseDesc] = useState("");
  const [newCasePriority, setNewCasePriority] = useState("MEDIUM");
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState(false);
  const [newCaseNote, setNewCaseNote] = useState("");

  // Graph Tab
  const [graphTxid, setGraphTxid] = useState("");
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [selectedGraphNode, setSelectedGraphNode] = useState<string | null>(null);

  // AI Analyst Tab
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiTargetTxid, setAiTargetTxid] = useState("");
  const [aiCaseId, setAiCaseId] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [loadingAI, setLoadingAI] = useState(false);

  // Knowledge Base Tab
  const [ragQuery, setRagQuery] = useState("What is a Peel Chain in Bitcoin analysis?");
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [loadingRAG, setLoadingRAG] = useState(false);

  // Reports Tab
  const [reportCaseId, setReportCaseId] = useState("");
  const [reportData, setReportData] = useState<any | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // Audit Logs Tab
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  // ML / Engine Tab
  const [modelStatus, setModelStatus] = useState<any | null>(null);
  const [modelEvaluation, setModelEvaluation] = useState<any | null>(null);
  const [loadingModels, setLoadingModels] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Auth Initialization
  useEffect(() => {
    const token = localStorage.getItem("sentinel_jwt_token");
    if (token) {
      api.getMe()
        .then((u) => setUser(u))
        .catch(() => {
          localStorage.removeItem("sentinel_jwt_token");
          setUser(null);
        });
    }
  }, []);

  // Fetch Dashboard Summary
  const loadDashboard = async () => {
    setLoadingDashboard(true);
    try {
      const data = await api.getDashboard();
      setDashboardData(data);
    } catch (err: any) {
      console.error("Dashboard error:", err);
    } finally {
      setLoadingDashboard(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // Sync Ingestion Trigger
  const handleSyncIngestion = async () => {
    setSyncingBitcoin(true);
    try {
      const res = await api.syncBitcoin(10, false);
      showToast(`Ingestion completed: Processed ${res.transactions_processed} TXs, Generated ${res.alerts_generated} Alerts.`);
      await loadDashboard();
      if (activeTab === "transactions") loadTransactions();
      if (activeTab === "alerts") loadAlerts();
    } catch (err: any) {
      showToast(`Sync error: ${err.message}`);
    } finally {
      setSyncingBitcoin(false);
    }
  };

  // Login Handlers
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await api.login(authEmail, authPassword);
      localStorage.setItem("sentinel_jwt_token", res.access_token);
      setUser(res.user);
      setIsAuthModalOpen(false);
      showToast(`Logged in as ${res.user.name} (${res.user.role})`);
      loadDashboard();
    } catch (err: any) {
      setAuthError(err.message || "Invalid credentials");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("sentinel_jwt_token");
    setUser(null);
    showToast("Signed out.");
  };

  // Load Transactions
  const loadTransactions = async () => {
    setLoadingTx(true);
    try {
      const params = new URLSearchParams();
      if (txRiskFilter) params.append("risk_level", txRiskFilter);
      if (txSearch) params.append("search", txSearch);
      params.append("limit", "50");
      const res = await api.getTransactions(params.toString());
      setTransactions(res.items);
      setTotalTxCount(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingTx(false);
    }
  };

  useEffect(() => {
    if (activeTab === "transactions") {
      loadTransactions();
    }
  }, [activeTab, txRiskFilter]);

  // Load Alerts
  const loadAlerts = async () => {
    try {
      const params = new URLSearchParams();
      if (alertSeverityFilter) params.append("severity", alertSeverityFilter);
      if (alertStatusFilter) params.append("status", alertStatusFilter);
      params.append("limit", "50");
      const res = await api.getAlerts(params.toString());
      setAlerts(res.items);
      setTotalAlertsCount(res.total);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === "alerts") {
      loadAlerts();
    }
  }, [activeTab, alertSeverityFilter, alertStatusFilter]);

  // Load Cases
  const loadCases = async () => {
    try {
      const list = await api.getCases();
      setCases(list);
      if (list.length > 0 && !selectedCase) {
        loadCaseDetail(list[0].id);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const loadCaseDetail = async (caseId: string) => {
    try {
      const c = await api.getCase(caseId);
      setSelectedCase(c);
      setReportCaseId(caseId);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === "cases") {
      loadCases();
    }
  }, [activeTab]);

  // Load Graph
  const loadGraph = async (txid: string) => {
    if (!txid) return;
    setLoadingGraph(true);
    try {
      const g = await api.getGraph(txid);
      setGraphData(g);
    } catch (err: any) {
      showToast(`Graph fetch error: ${err.message}`);
    } finally {
      setLoadingGraph(false);
    }
  };

  useEffect(() => {
    if (activeTab === "graph" && graphTxid) {
      loadGraph(graphTxid);
    }
  }, [activeTab]);

  // Load Models
  const loadModels = async () => {
    setLoadingModels(true);
    try {
      const [status, evalData] = await Promise.all([
        api.getModelStatus(),
        api.getModelEvaluation(),
      ]);
      setModelStatus(status);
      setModelEvaluation(evalData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    if (activeTab === "model_eval") {
      loadModels();
    }
  }, [activeTab]);

  // Load Audit
  const loadAuditLogs = async () => {
    setLoadingAudit(true);
    try {
      const res = await api.getAuditLogs(100);
      setAuditLogs(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    if (activeTab === "audit_logs") {
      loadAuditLogs();
    }
  }, [activeTab]);

  // Action: Create Case
  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;
    try {
      const c = await api.createCase({
        title: newCaseTitle,
        description: newCaseDesc,
        priority: newCasePriority,
        txids: selectedTx ? [selectedTx.txid] : selectedAlert ? [selectedAlert.txid] : [],
      });
      showToast(`Case "${c.title}" created successfully.`);
      setIsNewCaseModalOpen(false);
      setNewCaseTitle("");
      setNewCaseDesc("");
      loadCases();
      setSelectedCase(c);
      setActiveTab("cases");
    } catch (err: any) {
      showToast(`Error creating case: ${err.message}`);
    }
  };

  // Action: Add Case Note
  const handleAddCaseNote = async () => {
    if (!selectedCase || !newCaseNote.trim()) return;
    try {
      await api.addCaseNote(selectedCase.id, newCaseNote);
      showToast("Analyst note added.");
      setNewCaseNote("");
      loadCaseDetail(selectedCase.id);
    } catch (err: any) {
      showToast(`Error adding note: ${err.message}`);
    }
  };

  // Action: Update Alert Status
  const handleUpdateAlertStatus = async (alertId: string, newStatus: string) => {
    try {
      await api.updateAlertStatus(alertId, newStatus);
      showToast(`Alert status updated to ${newStatus}`);
      loadAlerts();
      if (selectedAlert && selectedAlert.id === alertId) {
        setSelectedAlert({ ...selectedAlert, status: newStatus as any });
      }
    } catch (err: any) {
      showToast(`Update error: ${err.message}`);
    }
  };

  // Action: Trigger AI Analysis
  const handleAIQuery = async (customPrompt?: string) => {
    const p = customPrompt || aiPrompt;
    if (!p.trim()) return;
    setLoadingAI(true);
    try {
      const res = await api.queryAIAnalyst(p, aiTargetTxid || undefined, aiCaseId || undefined, true);
      setAiAnalysis(res);
      showToast("AI forensic analysis generated.");
    } catch (err: any) {
      showToast(`AI query error: ${err.message}`);
    } finally {
      setLoadingAI(false);
    }
  };

  // Action: Trigger RAG Search
  const handleRAGSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ragQuery.trim()) return;
    setLoadingRAG(true);
    try {
      const res = await api.searchKnowledge(ragQuery, 4);
      setRagResults(res.results);
    } catch (err: any) {
      showToast(`RAG error: ${err.message}`);
    } finally {
      setLoadingRAG(false);
    }
  };

  // Action: Generate Report
  const handleGenerateReport = async (caseId: string) => {
    if (!caseId) return;
    setLoadingReport(true);
    try {
      const res = await api.generateReport(caseId);
      setReportData(res);
      showToast("Investigation report compiled.");
    } catch (err: any) {
      showToast(`Report error: ${err.message}`);
    } finally {
      setLoadingReport(false);
    }
  };

  // Quick jump helpers
  const jumpToGraph = (txid: string) => {
    setGraphTxid(txid);
    setActiveTab("graph");
    loadGraph(txid);
  };

  const jumpToAI = (txid: string, initialPrompt?: string) => {
    setAiTargetTxid(txid);
    if (initialPrompt) setAiPrompt(initialPrompt);
    setActiveTab("ai_analyst");
  };

  return (
    <div className="app-shell" style={{ display: "flex", minHeight: "100vh", background: "#0c1016" }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{ position: "fixed", bottom: "24px", right: "24px", zIndex: 1000, background: "#172b25", border: "1px solid #79dfb8", color: "#79dfb8", padding: "12px 18px", borderRadius: "6px", fontSize: "13px", boxShadow: "0 8px 24px rgba(0,0,0,0.5)", display: "flex", alignItems: "center", gap: "10px" }}>
          <Sparkles size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="sidebar" style={{ width: "240px", flexShrink: 0 }}>
        <div className="brand" style={{ display: "flex", alignItems: "center", gap: "10px", padding: "16px 12px 24px" }}>
          <div className="brand-symbol" style={{ background: "#172b25", color: "#79dfb8", width: "36px", height: "36px", borderRadius: "8px", display: "grid", placeItems: "center", fontWeight: "bold" }}>
            S
          </div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: "700", letterSpacing: "1px", color: "#f8fafc" }}>SENTINEL</div>
            <small style={{ color: "#79dfb8", letterSpacing: "1.5px", fontSize: "9px" }}>SOC ANALYST CORE</small>
          </div>
        </div>

        <div className="workspace-label" style={{ fontSize: "10px", letterSpacing: "1.5px", color: "#64748b", margin: "0 12px 8px", fontWeight: 700 }}>
          INVESTIGATION SUITE
        </div>

        <nav style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: isActive ? "#16202c" : "transparent",
                  color: isActive ? "#79dfb8" : "#94a3b8",
                  borderLeft: isActive ? "3px solid #79dfb8" : "3px solid transparent",
                  textAlign: "left",
                  fontSize: "12.5px",
                  fontWeight: isActive ? 600 : 400,
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div style={{ marginTop: "auto", padding: "16px 12px", borderTop: "1px solid #1e293b" }}>
          {user ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "#0d2b26", color: "#79dfb8", display: "grid", placeItems: "center", fontSize: "11px", fontWeight: "bold" }}>
                  {user.name.charAt(0)}
                </div>
                <div style={{ overflow: "hidden" }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{user.name}</div>
                  <div style={{ fontSize: "10px", color: "#79dfb8" }}>{user.role}</div>
                </div>
              </div>
              <button
                className="button small"
                onClick={handleLogout}
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", width: "100%", marginTop: "4px" }}
              >
                <LogOut size={13} /> Sign out
              </button>
            </div>
          ) : (
            <button
              className="button primary small"
              onClick={() => setIsAuthModalOpen(true)}
              style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", width: "100%" }}
            >
              <UserCheck size={14} /> Analyst Sign In
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: "24px 32px", overflowY: "auto", maxWidth: "1500px", margin: "0 auto", width: "100%" }}>
        {/* Top Header Strip */}
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
          <div>
            <h1 style={{ fontSize: "20px", fontWeight: 700, color: "#f8fafc", display: "flex", alignItems: "center", gap: "10px" }}>
              {NAV_ITEMS.find((n) => n.id === activeTab)?.label}
            </h1>
            <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
              AI-Powered Bitcoin Transaction Traffic Monitoring & Analysis (SIH-2026 Engine)
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              className="button"
              onClick={handleSyncIngestion}
              disabled={syncingBitcoin}
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
            >
              <RefreshCw size={13} className={syncingBitcoin ? "spinner" : ""} />
              {syncingBitcoin ? "Ingesting..." : "Sync Live Bitcoin"}
            </button>
            <button
              className="button primary"
              onClick={() => setIsNewCaseModalOpen(true)}
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
            >
              <Plus size={14} /> New Case
            </button>
          </div>
        </header>

        {/* ------------------------------------------------------------- */}
        {/* VIEW 1: DASHBOARD */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* KPI Metric Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px" }}>Total Ingested TXs</small>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: "6px 0" }}>
                  {dashboardData?.kpis.monitored_transactions.toLocaleString() ?? "..."}
                </div>
                <div style={{ fontSize: "11px", color: "#79dfb8", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Activity size={12} /> Active Blockstream Sync
                </div>
              </div>

              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px" }}>Active Alerts</small>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#e8b36a", margin: "6px 0" }}>
                  {dashboardData?.kpis.active_alerts.toLocaleString() ?? "..."}
                </div>
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  {dashboardData?.alert_severity_distribution.HIGH ?? 0} High / {dashboardData?.alert_severity_distribution.CRITICAL ?? 0} Critical
                </div>
              </div>

              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px" }}>High Risk TXs</small>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#f87171", margin: "6px 0" }}>
                  {dashboardData?.kpis.high_risk_transactions.toLocaleString() ?? "..."}
                </div>
                <div style={{ fontSize: "11px", color: "#f87171" }}>
                  Score ≥ 70 / 100
                </div>
              </div>

              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "1px" }}>Open Investigations</small>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#38bdf8", margin: "6px 0" }}>
                  {dashboardData?.kpis.open_cases.toLocaleString() ?? "..."}
                </div>
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  SOC Analyst Managed
                </div>
              </div>
            </div>

            {/* Ingestion Status Banner */}
            {dashboardData?.ingestion_status && (
              <div style={{ padding: "12px 16px", background: "#0d1b18", border: "1px solid #174238", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#79dfb8", boxShadow: "0 0 8px #79dfb8" }} />
                  <span style={{ fontSize: "12px", color: "#79dfb8", fontWeight: 600 }}>Esplora Ingestion Pipeline Connected</span>
                  <span style={{ fontSize: "12px", color: "#94a3b8" }}>| Latest Block: #{dashboardData.ingestion_status.latest_block}</span>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>({short(dashboardData.ingestion_status.block_hash, 6)})</span>
                </div>
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  Last synced: {timeAgo(dashboardData.ingestion_status.last_sync)}
                </div>
              </div>
            )}

            {/* Traffic Volume & Risk Charts */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc", marginBottom: "12px" }}>
                  Bitcoin Ingestion Volume & Transaction Traffic
                </h3>
                <div style={{ height: "240px", width: "100%" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={dashboardData?.traffic_series || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="txColor" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#79dfb8" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#79dfb8" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="hour_bucket" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} />
                      <Tooltip contentStyle={{ background: "#0c1016", borderColor: "#334155", fontSize: "11px" }} />
                      <Area type="monotone" dataKey="tx_count" stroke="#79dfb8" fillOpacity={1} fill="url(#txColor)" name="TX Count" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc", marginBottom: "12px" }}>
                  Risk Classification Distribution
                </h3>
                <div style={{ height: "240px", width: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {dashboardData && (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: "LOW", value: dashboardData.risk_distribution.LOW || 1, color: "#38bdf8" },
                            { name: "MEDIUM", value: dashboardData.risk_distribution.MEDIUM || 0, color: "#e8b36a" },
                            { name: "HIGH", value: dashboardData.risk_distribution.HIGH || 0, color: "#fb923c" },
                            { name: "CRITICAL", value: dashboardData.risk_distribution.CRITICAL || 0, color: "#f87171" },
                          ]}
                          innerRadius={55}
                          outerRadius={80}
                          paddingAngle={4}
                          dataKey="value"
                        >
                          {["#38bdf8", "#e8b36a", "#fb923c", "#f87171"].map((c, i) => (
                            <Cell key={`cell-${i}`} fill={c} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: "#0c1016", borderColor: "#334155", fontSize: "11px" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Action Panels (Recent Alerts + Recent Cases) */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc" }}>Recent Triaged Alerts</h3>
                  <button className="button small" onClick={() => setActiveTab("alerts")}>View All Alerts</button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {(dashboardData?.recent_alerts || []).slice(0, 4).map((a) => (
                    <div
                      key={a.id}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 12px", background: "#0a0f16", border: "1px solid #1e293b", borderRadius: "6px", cursor: "pointer" }}
                      onClick={() => {
                        setSelectedAlert(a);
                        setActiveTab("alerts");
                      }}
                    >
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>{a.title}</div>
                        <div style={{ fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>TX: {short(a.txid, 6)}</div>
                      </div>
                      <span className={`badge ${a.severity.toLowerCase()}`}>{a.severity}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc" }}>Active Cases</h3>
                  <button className="button small" onClick={() => setActiveTab("cases")}>Open Cases</button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {(dashboardData?.recent_cases || []).slice(0, 4).map((c) => (
                    <div
                      key={c.id}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 12px", background: "#0a0f16", border: "1px solid #1e293b", borderRadius: "6px", cursor: "pointer" }}
                      onClick={() => {
                        loadCaseDetail(c.id);
                        setActiveTab("cases");
                      }}
                    >
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>{c.title}</div>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>Status: {c.status} · {timeAgo(c.created_at)}</div>
                      </div>
                      <span className={`badge ${c.priority.toLowerCase()}`}>{c.priority}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 2: TRANSACTIONS EXPLORER */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "transactions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Filter Bar */}
            <div style={{ display: "flex", gap: "10px", alignItems: "center", background: "#11171f", padding: "12px 16px", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
                <input
                  type="text"
                  placeholder="Search by TXID or Address hash..."
                  value={txSearch}
                  onChange={(e) => setTxSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadTransactions()}
                  style={{ width: "100%", padding: "7px 10px 7px 32px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
                />
              </div>

              <select
                value={txRiskFilter}
                onChange={(e) => setTxRiskFilter(e.target.value)}
                style={{ padding: "7px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
              >
                <option value="">All Risk Levels</option>
                <option value="LOW">Low Risk</option>
                <option value="MEDIUM">Medium Risk</option>
                <option value="HIGH">High Risk</option>
                <option value="CRITICAL">Critical Risk</option>
              </select>

              <button className="button small" onClick={loadTransactions}>
                <Filter size={13} /> Filter
              </button>
            </div>

            {/* Transactions Table & Detail Drawer */}
            <div style={{ display: "grid", gridTemplateColumns: selectedTx ? "1.4fr 1fr" : "1fr", gap: "16px" }}>
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", fontSize: "12px", color: "#94a3b8" }}>
                  <span>Showing {transactions.length} of {totalTxCount} transactions</span>
                  <span>Click a row to inspect UTXO forensics</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid #1e293b", textAlign: "left", color: "#64748b" }}>
                        <th style={{ padding: "8px 6px" }}>TXID</th>
                        <th style={{ padding: "8px 6px" }}>Total Output (BTC)</th>
                        <th style={{ padding: "8px 6px" }}>In / Out</th>
                        <th style={{ padding: "8px 6px" }}>Fee Rate</th>
                        <th style={{ padding: "8px 6px" }}>Risk Score</th>
                        <th style={{ padding: "8px 6px" }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr
                          key={tx.txid}
                          onClick={() => setSelectedTx(tx)}
                          style={{
                            borderBottom: "1px solid #16202c",
                            cursor: "pointer",
                            background: selectedTx?.txid === tx.txid ? "#16222f" : "transparent",
                          }}
                        >
                          <td style={{ padding: "10px 6px", fontFamily: "monospace", color: "#79dfb8" }}>
                            {short(tx.txid, 6)}
                          </td>
                          <td style={{ padding: "10px 6px", color: "#f8fafc" }}>{btc(tx.total_output_sats)} BTC</td>
                          <td style={{ padding: "10px 6px", color: "#94a3b8" }}>{tx.input_count} → {tx.output_count}</td>
                          <td style={{ padding: "10px 6px", color: "#94a3b8" }}>{tx.fee_rate?.toFixed(1) || "1.0"} sat/vB</td>
                          <td style={{ padding: "10px 6px" }}>
                            <span className={`badge ${tx.risk_level.toLowerCase()}`}>
                              {tx.risk_score} ({tx.risk_level})
                            </span>
                          </td>
                          <td style={{ padding: "10px 6px" }}>
                            {tx.is_flagged ? (
                              <span style={{ color: "#f87171", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}>
                                <AlertTriangle size={12} /> Flagged
                              </span>
                            ) : (
                              <span style={{ color: "#79dfb8", fontSize: "11px" }}>Normal</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Transaction Detail Panel */}
              {selectedTx && (
                <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px", height: "fit-content" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: "12px", marginBottom: "12px" }}>
                    <div>
                      <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc" }}>Transaction Forensics</h3>
                      <div style={{ fontSize: "10px", color: "#79dfb8", fontFamily: "monospace" }}>{selectedTx.txid}</div>
                    </div>
                    <button className="button small" onClick={() => setSelectedTx(null)}>✕</button>
                  </div>

                  {/* Actions Strip */}
                  <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
                    <button className="button primary small" onClick={() => jumpToGraph(selectedTx.txid)}>
                      <GitBranch size={13} /> Graph Explorer
                    </button>
                    <button className="button small" onClick={() => jumpToAI(selectedTx.txid, `Analyze transaction ${selectedTx.txid} for structural anomalies and peeling patterns.`)}>
                      <Bot size={13} /> Ask AI Analyst
                    </button>
                  </div>

                  {/* Risk Breakdown */}
                  <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b", marginBottom: "14px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{ fontSize: "11px", color: "#94a3b8" }}>Risk Assessment</span>
                      <span className={`badge ${selectedTx.risk_level.toLowerCase()}`}>{selectedTx.risk_level} ({selectedTx.risk_score}/100)</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                      ML Anomaly Score: <b>{selectedTx.anomaly_score}</b> (Isolation Forest)
                    </div>
                  </div>

                  {/* Inputs & Outputs List */}
                  <div style={{ marginBottom: "12px" }}>
                    <small style={{ color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", fontSize: "10px" }}>Inputs ({selectedTx.inputs?.length || 0})</small>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "4px" }}>
                      {(selectedTx.inputs || []).map((inp, idx) => (
                        <div key={idx} style={{ fontSize: "11px", display: "flex", justifyContent: "space-between", padding: "6px", background: "#0a0f16", borderRadius: "4px" }}>
                          <span style={{ fontFamily: "monospace", color: "#38bdf8" }}>{short(inp.address || "Unparsed", 8)}</span>
                          <span>{btc(inp.value_sats)} BTC</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <small style={{ color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", fontSize: "10px" }}>Outputs ({selectedTx.outputs?.length || 0})</small>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "4px" }}>
                      {(selectedTx.outputs || []).map((out, idx) => (
                        <div key={idx} style={{ fontSize: "11px", display: "flex", justifyContent: "space-between", padding: "6px", background: "#0a0f16", borderRadius: "4px" }}>
                          <span style={{ fontFamily: "monospace", color: "#79dfb8" }}>{short(out.address || "OP_RETURN", 8)}</span>
                          <span>{btc(out.value_sats)} BTC</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 3: ALERT QUEUE */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "alerts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Filter controls */}
            <div style={{ display: "flex", gap: "10px", background: "#11171f", padding: "12px 16px", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <select
                value={alertSeverityFilter}
                onChange={(e) => setAlertSeverityFilter(e.target.value)}
                style={{ padding: "7px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <select
                value={alertStatusFilter}
                onChange={(e) => setAlertStatusFilter(e.target.value)}
                style={{ padding: "7px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
              >
                <option value="">All Statuses</option>
                <option value="NEW">New</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="ESCALATED">Escalated</option>
                <option value="RESOLVED">Resolved</option>
                <option value="FALSE_POSITIVE">False Positive</option>
              </select>
            </div>

            {/* Alert List & Triage Inspector */}
            <div style={{ display: "grid", gridTemplateColumns: selectedAlert ? "1.2fr 1fr" : "1fr", gap: "16px" }}>
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {alerts.map((al) => (
                    <div
                      key={al.id}
                      onClick={() => setSelectedAlert(al)}
                      style={{
                        padding: "12px 14px",
                        background: selectedAlert?.id === al.id ? "#16202c" : "#0a0f16",
                        border: "1px solid #1e293b",
                        borderLeft: `4px solid ${SEVERITY_COLORS[al.severity] || "#38bdf8"}`,
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "4px" }}>
                        <div style={{ fontWeight: 600, fontSize: "13px", color: "#f8fafc" }}>{al.title}</div>
                        <span className={`badge ${al.severity.toLowerCase()}`}>{al.severity}</span>
                      </div>
                      <p style={{ fontSize: "11.5px", color: "#94a3b8", margin: "4px 0" }}>{al.reason}</p>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10.5px", color: "#64748b", marginTop: "8px" }}>
                        <span style={{ fontFamily: "monospace" }}>TX: {short(al.txid, 8)}</span>
                        <span>Status: <b style={{ color: "#79dfb8" }}>{al.status}</b> · {timeAgo(al.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Alert Triage Drawer */}
              {selectedAlert && (
                <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px", height: "fit-content" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: "10px", marginBottom: "12px" }}>
                    <div>
                      <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc" }}>{selectedAlert.title}</h3>
                      <small style={{ color: "#64748b" }}>Alert ID: {selectedAlert.id}</small>
                    </div>
                    <button className="button small" onClick={() => setSelectedAlert(null)}>✕</button>
                  </div>

                  <div style={{ fontSize: "12px", color: "#cbd5e1", marginBottom: "14px", lineHeight: 1.6 }}>
                    {selectedAlert.reason}
                  </div>

                  {/* Heuristic Signals & Evidence */}
                  <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b", marginBottom: "16px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 600, color: "#79dfb8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                      Detection Signals
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px" }}>
                      <div><b>Detection Method:</b> {selectedAlert.detection_method}</div>
                      <div><b>Risk Score:</b> {selectedAlert.risk_score} / 100</div>
                      <div><b>Anomaly Score:</b> {selectedAlert.anomaly_score} / 100</div>
                      <div style={{ wordBreak: "break-all", fontFamily: "monospace", color: "#94a3b8" }}>
                        TX: {selectedAlert.txid}
                      </div>
                    </div>
                  </div>

                  {/* Status Transition Buttons */}
                  <div style={{ marginBottom: "16px" }}>
                    <small style={{ color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", fontSize: "10px" }}>Change Alert Triage Status</small>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                      <button className="button small" onClick={() => handleUpdateAlertStatus(selectedAlert.id, "UNDER_REVIEW")}>Under Review</button>
                      <button className="button small" onClick={() => handleUpdateAlertStatus(selectedAlert.id, "ESCALATED")}>Escalate</button>
                      <button className="button small" onClick={() => handleUpdateAlertStatus(selectedAlert.id, "RESOLVED")}>Resolve</button>
                      <button className="button small" onClick={() => handleUpdateAlertStatus(selectedAlert.id, "FALSE_POSITIVE")}>False Positive</button>
                    </div>
                  </div>

                  {/* Action Shortcuts */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <button className="button primary" onClick={() => jumpToGraph(selectedAlert.txid)}>
                      <GitBranch size={14} /> Open in Graph Explorer
                    </button>
                    <button className="button" onClick={() => jumpToAI(selectedAlert.txid, `Why was alert "${selectedAlert.title}" flagged for transaction ${selectedAlert.txid}?`)}>
                      <Bot size={14} /> AI Deep-Dive Analysis
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 4: INVESTIGATION CASES */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "cases" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "16px" }}>
            {/* Case List */}
            <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc" }}>Active Investigation Cases</h3>
                <button className="button primary small" onClick={() => setIsNewCaseModalOpen(true)}>
                  <Plus size={12} /> New
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {cases.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => loadCaseDetail(c.id)}
                    style={{
                      padding: "12px",
                      background: selectedCase?.id === c.id ? "#16202c" : "#0a0f16",
                      border: "1px solid #1e293b",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "4px" }}>
                      <div style={{ fontWeight: 600, fontSize: "12.5px", color: "#f8fafc" }}>{c.title}</div>
                      <span className={`badge ${c.priority.toLowerCase()}`}>{c.priority}</span>
                    </div>
                    <p style={{ fontSize: "11px", color: "#94a3b8", margin: "4px 0" }}>{c.description || "No description provided."}</p>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#64748b", marginTop: "6px" }}>
                      <span>Status: <b style={{ color: "#79dfb8" }}>{c.status}</b></span>
                      <span>{c.transaction_count || 0} TXs attached</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Case Details Board */}
            {selectedCase ? (
              <div className="panel" style={{ padding: "20px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #1e293b", paddingBottom: "16px", marginBottom: "16px" }}>
                  <div>
                    <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>{selectedCase.title}</h2>
                    <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{selectedCase.description}</p>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px" }}>
                      Lead: <b>{selectedCase.lead_investigator_name || "Unassigned"}</b> · Created: {timeAgo(selectedCase.created_at)}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px" }}>
                    <button className="button small" onClick={() => {
                      setReportCaseId(selectedCase.id);
                      handleGenerateReport(selectedCase.id);
                      setActiveTab("reports");
                    }}>
                      <FileCheck size={13} /> Compile Report
                    </button>
                  </div>
                </div>

                {/* Attached Transactions */}
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "12px", fontWeight: 600, color: "#79dfb8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                    Attached Subject Transactions ({selectedCase.transactions?.length || 0})
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {(selectedCase.transactions || []).map((tx) => (
                      <div key={tx.txid} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "#0a0f16", borderRadius: "6px", border: "1px solid #1e293b" }}>
                        <div>
                          <span style={{ fontFamily: "monospace", color: "#79dfb8", fontSize: "11.5px" }}>{short(tx.txid, 8)}</span>
                          <span style={{ marginLeft: "12px", color: "#f8fafc", fontSize: "11.5px" }}>{btc(tx.total_output_sats)} BTC</span>
                        </div>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button className="button small" onClick={() => jumpToGraph(tx.txid)}>Graph</button>
                          <button className="button small" onClick={() => jumpToAI(tx.txid, `Analyze attached transaction ${tx.txid} in the context of case ${selectedCase.title}.`)}>AI</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Investigation Timeline */}
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "12px", fontWeight: 600, color: "#79dfb8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                    Forensic Activity Timeline
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {(selectedCase.timeline || []).map((ev) => (
                      <div key={ev.id} style={{ display: "flex", gap: "10px", padding: "8px 12px", background: "#0a0f16", borderRadius: "6px", border: "1px solid #1e293b", fontSize: "11.5px" }}>
                        <Clock size={14} style={{ color: "#38bdf8", flexShrink: 0, marginTop: "2px" }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ color: "#f8fafc", fontWeight: 500 }}>{ev.summary}</div>
                          <div style={{ color: "#64748b", fontSize: "10px" }}>By {ev.actor_name || "System"} · {timeAgo(ev.created_at)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Case Notes & Analyst Input */}
                <div>
                  <h4 style={{ fontSize: "12px", fontWeight: 600, color: "#79dfb8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                    Analyst Working Notes
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "12px" }}>
                    {(selectedCase.notes || []).map((n) => (
                      <div key={n.id} style={{ padding: "8px 12px", background: "#0a0f16", borderRadius: "6px", border: "1px solid #1e293b", fontSize: "11.5px" }}>
                        <p style={{ color: "#cbd5e1", margin: 0 }}>{n.note}</p>
                        <div style={{ color: "#64748b", fontSize: "10px", marginTop: "4px" }}>
                          {n.author_name || "Analyst"} · {timeAgo(n.created_at)}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: "flex", gap: "8px" }}>
                    <input
                      type="text"
                      placeholder="Add investigation observation or hypothesis..."
                      value={newCaseNote}
                      onChange={(e) => setNewCaseNote(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddCaseNote()}
                      style={{ flex: 1, padding: "8px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
                    />
                    <button className="button primary small" onClick={handleAddCaseNote}>
                      <Send size={13} /> Add Note
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: "grid", placeItems: "center", color: "#64748b", fontSize: "13px" }}>
                Select a case to inspect evidence and timeline.
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 5: GRAPH EXPLORER */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "graph" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Search and control bar */}
            <div style={{ display: "flex", gap: "10px", background: "#11171f", padding: "12px 16px", borderRadius: "8px", border: "1px solid #1e293b", alignItems: "center" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <GitBranch size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
                <input
                  type="text"
                  placeholder="Enter Transaction ID (TXID) to render UTXO flow graph..."
                  value={graphTxid}
                  onChange={(e) => setGraphTxid(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadGraph(graphTxid)}
                  style={{ width: "100%", padding: "8px 10px 8px 32px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
                />
              </div>
              <button className="button primary" onClick={() => loadGraph(graphTxid)} disabled={loadingGraph}>
                <RefreshCw size={13} className={loadingGraph ? "spinner" : ""} /> Render Graph
              </button>
            </div>

            {/* Cytoscape Canvas */}
            <div style={{ height: "620px", width: "100%" }}>
              <Graph
                graphData={graphData}
                loading={loadingGraph}
                selectedNodeId={selectedGraphNode}
                onSelectNode={(nodeId, type) => {
                  setSelectedGraphNode(nodeId);
                  showToast(`Selected ${type}: ${short(nodeId, 8)}`);
                }}
              />
            </div>

            {/* Graph Context Footer */}
            {graphData && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#94a3b8", background: "#11171f", padding: "10px 16px", borderRadius: "6px", border: "1px solid #1e293b" }}>
                <span>Graph Rendered: <b>{graphData.node_count}</b> Nodes, <b>{graphData.edge_count}</b> Edges</span>
                <span style={{ color: "#e8b36a" }}>{graphData.disclaimer}</span>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 6: AI ANALYST (GEMINI + FORENSIC RAG) */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "ai_analyst" && (
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px" }}>
            {/* Input & Prompt Engineering Panel */}
            <div className="panel" style={{ padding: "20px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                <Sparkles size={18} style={{ color: "#79dfb8" }} />
                <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc" }}>AI Security Analyst Engine</h3>
              </div>
              <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
                Grounds ML anomaly scores and rule violations with Bitcoin forensics doctrines and generates defensible, evidence-backed security assessments.
              </p>

              {/* Target Context Inputs */}
              <div style={{ display: "flex", gap: "10px", marginBottom: "12px" }}>
                <input
                  type="text"
                  placeholder="Optional Target TXID..."
                  value={aiTargetTxid}
                  onChange={(e) => setAiTargetTxid(e.target.value)}
                  style={{ flex: 1, padding: "8px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
                />
              </div>

              {/* Quick Prompt Pills */}
              <div style={{ marginBottom: "12px" }}>
                <small style={{ color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", fontSize: "10px" }}>Quick Investigation Prompts</small>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                  <button className="button small" onClick={() => handleAIQuery("Explain why this transaction anomaly score was flagged as high.")}>
                    Why flagged?
                  </button>
                  <button className="button small" onClick={() => handleAIQuery("What are the recommended next steps to investigate this peeling chain?")}>
                    Investigate Next
                  </button>
                  <button className="button small" onClick={() => handleAIQuery("Summarize the structural Bitcoin transaction patterns and risk indicators.")}>
                    Pattern Summary
                  </button>
                  <button className="button small" onClick={() => handleAIQuery("Could this equal-split transaction be CoinJoin or mixer traffic?")}>
                    CoinJoin Check
                  </button>
                </div>
              </div>

              {/* Custom Prompt Box */}
              <textarea
                rows={4}
                placeholder="Ask the AI Analyst to evaluate specific transaction traffic, explain heuristics, or draft case findings..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                style={{ width: "100%", padding: "10px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginBottom: "12px", resize: "vertical" }}
              />

              <button
                className="button primary"
                onClick={() => handleAIQuery()}
                disabled={loadingAI}
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", width: "100%" }}
              >
                <Bot size={15} className={loadingAI ? "spinner" : ""} />
                {loadingAI ? "Analyzing Blockchain Evidence..." : "Run AI Analyst Analysis"}
              </button>
            </div>

            {/* Structured AI Analysis Output */}
            <div className="panel" style={{ padding: "20px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px", overflowY: "auto", maxHeight: "700px" }}>
              {aiAnalysis ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ borderBottom: "1px solid #1e293b", paddingBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#79dfb8" }}>Executive Analyst Summary</h4>
                      <span className="badge low">{aiAnalysis.model_used}</span>
                    </div>
                    <p style={{ fontSize: "12.5px", color: "#f8fafc", lineHeight: 1.6 }}>{aiAnalysis.summary}</p>
                  </div>

                  {/* Facts vs Indications Breakdown */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b" }}>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#38bdf8", marginBottom: "6px" }}>VERIFIED FACTS</div>
                      <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#cbd5e1" }}>
                        {aiAnalysis.facts.map((f, i) => <li key={i}>{f}</li>)}
                      </ul>
                    </div>

                    <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b" }}>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#e8b36a", marginBottom: "6px" }}>MODEL INDICATIONS</div>
                      <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#cbd5e1" }}>
                        {aiAnalysis.model_indications.map((mi, i) => <li key={i}>{mi}</li>)}
                      </ul>
                    </div>
                  </div>

                  {/* Recommended Next Steps */}
                  <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b" }}>
                    <div style={{ fontSize: "11px", fontWeight: 600, color: "#79dfb8", marginBottom: "6px" }}>RECOMMENDED INVESTIGATION STEPS</div>
                    <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#cbd5e1" }}>
                      {aiAnalysis.recommended_steps.map((step, i) => <li key={i}>{step}</li>)}
                    </ul>
                  </div>

                  {/* Legal & Ethical Limitations */}
                  <div style={{ background: "#16130d", border: "1px solid #422006", padding: "10px 12px", borderRadius: "6px", fontSize: "11px", color: "#e8b36a" }}>
                    <b>Analytical Limitation:</b> {aiAnalysis.limitations}
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", placeItems: "center", height: "300px", color: "#64748b", textAlign: "center" }}>
                  <div>
                    <Bot size={36} style={{ marginBottom: "8px", opacity: 0.5 }} />
                    <p style={{ margin: 0, fontSize: "13px" }}>AI Analyst is idle.</p>
                    <small>Submit a prompt or click a quick pill to generate an assessment.</small>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 7: FORENSIC KNOWLEDGE BASE (RAG) */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "knowledge_base" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ background: "#11171f", padding: "16px", borderRadius: "8px", border: "1px solid #1e293b" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc", marginBottom: "8px" }}>
                Bitcoin Forensic Doctrine & Typology Vector Search (RAG)
              </h3>
              <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "14px" }}>
                Semantic search over the embedded knowledge base covering Peel Chains, CoinJoin heuristics, Fan-out typologies, and chain analysis doctrines.
              </p>

              <form onSubmit={handleRAGSearch} style={{ display: "flex", gap: "10px" }}>
                <input
                  type="text"
                  placeholder="Ask a technical blockchain question or search typologies (e.g. 'Peel chain heuristics', 'CoinJoin signatures')..."
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  style={{ flex: 1, padding: "8px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px" }}
                />
                <button type="submit" className="button primary" disabled={loadingRAG}>
                  <Search size={14} className={loadingRAG ? "spinner" : ""} /> Search Docs
                </button>
              </form>
            </div>

            {/* Results Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              {ragResults.map((r, i) => (
                <div key={i} className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#79dfb8", textTransform: "uppercase" }}>
                      {r.metadata?.category || "DOC"} · Similarity: {(r.similarity * 100).toFixed(1)}%
                    </span>
                    <span className="badge low">{r.metadata?.doc_id || "doc"}</span>
                  </div>
                  <h4 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc", marginBottom: "8px" }}>
                    {r.metadata?.title || "Forensic Reference"}
                  </h4>
                  <p style={{ fontSize: "12px", color: "#cbd5e1", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                    {r.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 8: INVESTIGATION REPORTS */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "reports" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ background: "#11171f", padding: "16px", borderRadius: "8px", border: "1px solid #1e293b", display: "flex", alignItems: "center", gap: "12px" }}>
              <select
                value={reportCaseId}
                onChange={(e) => setReportCaseId(e.target.value)}
                style={{ padding: "8px 12px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", minWidth: "260px" }}
              >
                <option value="">Select an Investigation Case</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>{c.title} ({c.id})</option>
                ))}
              </select>

              <button
                className="button primary"
                onClick={() => handleGenerateReport(reportCaseId)}
                disabled={!reportCaseId || loadingReport}
              >
                <FileCheck size={14} className={loadingReport ? "spinner" : ""} /> Generate Case Report
              </button>

              {reportData && (
                <button
                  className="button"
                  onClick={() => downloadReportJSON(reportData, `sentinel-case-${reportCaseId}.json`)}
                >
                  <Download size={14} /> Export JSON
                </button>
              )}
            </div>

            {reportData && (
              <div className="panel" style={{ padding: "24px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ borderBottom: "1px solid #1e293b", paddingBottom: "16px" }}>
                  <div style={{ fontSize: "10px", color: "#79dfb8", letterSpacing: "1.5px", fontWeight: 700 }}>OFFICIAL SOC INVESTIGATION REPORT</div>
                  <h2 style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", marginTop: "4px" }}>{reportData.case_metadata?.title}</h2>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                    Generated: {reportData.generated_at} | Priority: <b>{reportData.case_metadata?.priority}</b> | Status: <b>{reportData.case_metadata?.status}</b>
                  </div>
                </div>

                {/* Evidence Summary Table */}
                <div>
                  <h4 style={{ fontSize: "12px", fontWeight: 600, color: "#79dfb8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                    Attached Subject Transactions ({reportData.attached_transactions?.length || 0})
                  </h4>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid #1e293b", textAlign: "left", color: "#64748b" }}>
                        <th style={{ padding: "6px" }}>TXID</th>
                        <th style={{ padding: "6px" }}>Total Volume</th>
                        <th style={{ padding: "6px" }}>Risk Score</th>
                        <th style={{ padding: "6px" }}>Flagged</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData.attached_transactions || []).map((t: any) => (
                        <tr key={t.txid} style={{ borderBottom: "1px solid #16202c" }}>
                          <td style={{ padding: "6px", fontFamily: "monospace", color: "#79dfb8" }}>{t.txid}</td>
                          <td style={{ padding: "6px" }}>{btc(t.total_output_sats)} BTC</td>
                          <td style={{ padding: "6px" }}><span className={`badge ${t.risk_level.toLowerCase()}`}>{t.risk_score}</span></td>
                          <td style={{ padding: "6px" }}>{t.is_flagged ? "Yes" : "No"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Regulatory / Legal Disclaimer */}
                <div style={{ background: "#0a0f16", padding: "12px", borderRadius: "6px", border: "1px solid #1e293b", fontSize: "11px", color: "#94a3b8" }}>
                  <b>Legal Disclaimer:</b> {reportData.disclaimer}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 9: AUDIT LOGS */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "audit_logs" && (
          <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: "#f8fafc" }}>Security Operations Audit Trail</h3>
              <button className="button small" onClick={loadAuditLogs}>
                <RefreshCw size={12} className={loadingAudit ? "spinner" : ""} /> Refresh
              </button>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #1e293b", textAlign: "left", color: "#64748b" }}>
                    <th style={{ padding: "8px 6px" }}>Timestamp</th>
                    <th style={{ padding: "8px 6px" }}>Actor</th>
                    <th style={{ padding: "8px 6px" }}>Action</th>
                    <th style={{ padding: "8px 6px" }}>Target</th>
                    <th style={{ padding: "8px 6px" }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log) => (
                    <tr key={log.id} style={{ borderBottom: "1px solid #16202c" }}>
                      <td style={{ padding: "8px 6px", color: "#64748b", whiteSpace: "nowrap" }}>{timeAgo(log.created_at)}</td>
                      <td style={{ padding: "8px 6px", color: "#38bdf8" }}>{log.actor_name || "System"}</td>
                      <td style={{ padding: "8px 6px", fontWeight: 600, color: "#f8fafc" }}>{log.action}</td>
                      <td style={{ padding: "8px 6px", color: "#79dfb8" }}>{log.target_type} ({short(log.target_id || "", 6)})</td>
                      <td style={{ padding: "8px 6px", color: "#94a3b8", fontFamily: "monospace", fontSize: "11px" }}>{log.details_json || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* VIEW 10: ML MODEL STATUS & EVALUATION */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "model_eval" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              {/* Isolation Forest Status */}
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#79dfb8", marginBottom: "10px", textTransform: "uppercase" }}>
                  Isolation Forest Anomaly Model
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "#cbd5e1" }}>
                  <div><b>Status:</b> {modelStatus?.isolation_forest?.status || "READY"}</div>
                  <div><b>Contamination:</b> {modelStatus?.isolation_forest?.contamination ?? 0.05}</div>
                  <div><b>Trees (n_estimators):</b> {modelStatus?.isolation_forest?.n_estimators ?? 100}</div>
                  <div><b>Dataset Size:</b> {modelStatus?.isolation_forest?.training_samples ?? 120} samples</div>
                </div>
              </div>

              {/* Engine Metrics */}
              <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#38bdf8", marginBottom: "10px", textTransform: "uppercase" }}>
                  Feature Pipeline Specs
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", color: "#cbd5e1" }}>
                  <div><b>Feature Vector Dimensions:</b> 14 extracted features</div>
                  <div><b>Normalization:</b> Robust Percentile Scaling (0-100)</div>
                  <div><b>Supported Heuristics:</b> 8 configurable rule detectors</div>
                  <div><b>Offline Capability:</b> 100% deterministic fallback enabled</div>
                </div>
              </div>
            </div>

            {/* Feature Weighting Preview */}
            <div className="panel" style={{ padding: "16px", background: "#11171f", border: "1px solid #1e293b", borderRadius: "8px" }}>
              <h3 style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc", marginBottom: "12px" }}>
                Evaluated Feature Weights in Risk Fusion
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px", fontSize: "11.5px" }}>
                {[
                  { name: "Peel Chain Pattern", weight: "25%", color: "#f87171" },
                  { name: "Fan-Out Ratio", weight: "20%", color: "#fb923c" },
                  { name: "Equal Split (CoinJoin)", weight: "15%", color: "#e8b36a" },
                  { name: "High Consolidation", weight: "15%", color: "#38bdf8" },
                  { name: "Abnormal Fee Rate", weight: "10%", color: "#79dfb8" },
                  { name: "Dust Attack Signature", weight: "15%", color: "#c084fc" },
                ].map((f, i) => (
                  <div key={i} style={{ padding: "8px 12px", background: "#0a0f16", borderRadius: "6px", border: "1px solid #1e293b", display: "flex", justifyContent: "space-between" }}>
                    <span>{f.name}</span>
                    <b style={{ color: f.color }}>{f.weight}</b>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ------------------------------------------------------------- */}
      {/* MODAL: CREATE CASE */}
      {/* ------------------------------------------------------------- */}
      {isNewCaseModalOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "grid", placeItems: "center", zIndex: 1000 }}>
          <div className="panel" style={{ width: "460px", padding: "24px", background: "#11171f", border: "1px solid #334155", borderRadius: "8px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#f8fafc", marginBottom: "12px" }}>Create Investigation Case</h3>
            <form onSubmit={handleCreateCase} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "11px", color: "#94a3b8" }}>Case Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Investigation into suspicious peel chain on Block 850000"
                  value={newCaseTitle}
                  onChange={(e) => setNewCaseTitle(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginTop: "4px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "#94a3b8" }}>Priority Level</label>
                <select
                  value={newCasePriority}
                  onChange={(e) => setNewCasePriority(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginTop: "4px" }}
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "#94a3b8" }}>Investigation Synopsis</label>
                <textarea
                  rows={3}
                  placeholder="Describe preliminary indicators or investigative lead..."
                  value={newCaseDesc}
                  onChange={(e) => setNewCaseDesc(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginTop: "4px", resize: "none" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" className="button" onClick={() => setIsNewCaseModalOpen(false)}>Cancel</button>
                <button type="submit" className="button primary">Initialize Case</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MODAL: AUTHENTICATION */}
      {/* ------------------------------------------------------------- */}
      {isAuthModalOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "grid", placeItems: "center", zIndex: 1000 }}>
          <div className="panel" style={{ width: "380px", padding: "24px", background: "#11171f", border: "1px solid #334155", borderRadius: "8px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#f8fafc", marginBottom: "4px" }}>Sentinel SOC Sign In</h3>
            <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "16px" }}>Default: analyst@sentinel.sec / analyst123</p>

            {authError && (
              <div style={{ padding: "8px 10px", background: "#450a0a", border: "1px solid #f87171", borderRadius: "4px", color: "#fca5a5", fontSize: "11px", marginBottom: "12px" }}>
                {authError}
              </div>
            )}

            <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "11px", color: "#94a3b8" }}>Email</label>
                <input
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginTop: "4px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "11px", color: "#94a3b8" }}>Password</label>
                <input
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: "#0a0f16", border: "1px solid #334155", borderRadius: "6px", color: "#f8fafc", fontSize: "12px", marginTop: "4px" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" className="button" onClick={() => setIsAuthModalOpen(false)}>Cancel</button>
                <button type="submit" className="button primary">Sign In</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
