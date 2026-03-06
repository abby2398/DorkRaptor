import { useState, useEffect, useRef } from "react";
import { api, formatDate, SEVERITY_COLORS, CATEGORY_LABELS, SOURCE_LABELS, truncateUrl } from "../utils/api";
import "./ScanPage.css";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export default function ScanPage({ scanId, onNavigate }) {
  const [scan, setScan] = useState(null);
  const [findings, setFindings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState({ severity: "", category: "", source: "" });
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedFinding, setSelectedFinding] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!scanId) { onNavigate("dashboard"); return; }
    loadScan();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [scanId]);

  const loadScan = async () => {
    try {
      const scanData = await api.getScan(scanId);
      setScan(scanData);
      setLoading(false);

      if (scanData.status === "completed" || scanData.status === "failed") {
        await loadFindings(scanData);
        await loadStats();
      } else {
        startPolling();
      }
    } catch (e) {
      setLoading(false);
    }
  };

  const loadFindings = async (scanData) => {
    try {
      const f = await api.getScanFindings(scanId, activeFilter);
      setFindings(f);
    } catch (e) {}
  };

  const loadStats = async () => {
    try {
      const s = await api.getScanStats(scanId);
      setStats(s);
    } catch (e) {}
  };

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      try {
        const scanData = await api.getScan(scanId);
        setScan(scanData);

        if (scanData.status === "completed" || scanData.status === "failed") {
          clearInterval(pollRef.current);
          await loadFindings(scanData);
          await loadStats();
        }
      } catch (e) {}
    }, 2500);
  };

  const applyFilter = async (newFilter) => {
    const merged = { ...activeFilter, ...newFilter };
    setActiveFilter(merged);
    try {
      const f = await api.getScanFindings(scanId, merged);
      setFindings(f);
    } catch (e) {}
  };

  const clearFilter = (key) => applyFilter({ [key]: "" });

  if (loading) {
    return (
      <div className="page scan-page loading-state">
        <div className="loading-center">
          <div className="spinner" style={{ width: 32, height: 32 }} />
          <p>Loading scan data...</p>
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="page scan-page">
        <div className="empty-state">
          <div className="empty-state-icon">⚠</div>
          <div className="empty-state-title">Scan not found</div>
          <button className="btn btn-ghost" onClick={() => onNavigate("dashboard")}>← Back</button>
        </div>
      </div>
    );
  }

  const progress = scan.status === "completed" ? 100 :
    scan.dorks_total > 0 ? Math.min(Math.floor((scan.dorks_executed / scan.dorks_total) * 95), 95) : 5;

  const isRunning = scan.status === "running" || scan.status === "pending";
  const categoryData = stats?.category_distribution || {};
  const severityData = stats?.severity_distribution || {};

  return (
    <div className="page scan-page animate-in">
      {/* Header */}
      <div className="scan-header">
        <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("dashboard")}>← Back</button>
        <div className="scan-title-area">
          <h1 className="scan-domain-title">{scan.domain}</h1>
          <div className="scan-meta-row">
            <span className={`badge ${scan.status}`} style={{ textTransform: "capitalize" }}>
              <span className={`status-dot ${scan.status}`} />
              {scan.status}
            </span>
            <span className="scan-time-meta mono">Started {formatDate(scan.created_at)}</span>
            {scan.completed_at && (
              <span className="scan-time-meta mono">Completed {formatDate(scan.completed_at)}</span>
            )}
          </div>
        </div>
      </div>

      {/* Progress bar (when running) */}
      {isRunning && (
        <div className="scan-progress-section animate-in">
          <div className="progress-info">
            <span>Scanning in progress...</span>
            <span className="mono">{progress}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-detail mono">
            {scan.dorks_executed} / {scan.dorks_total || "?"} dorks executed
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="severity-summary-grid">
        {[
          { key: "critical", label: "Critical", count: scan.critical_count, color: "var(--severity-critical)" },
          { key: "high", label: "High", count: scan.high_count, color: "var(--severity-high)" },
          { key: "medium", label: "Medium", count: scan.medium_count, color: "var(--severity-medium)" },
          { key: "low", label: "Low", count: scan.low_count, color: "var(--severity-low)" },
          { key: "info", label: "Info", count: scan.info_count, color: "var(--severity-info)" },
          { key: "total", label: "Total", count: scan.total_findings, color: "var(--accent-primary)" },
        ].map((item) => (
          <div
            key={item.key}
            className={`severity-card ${activeFilter.severity === item.key ? "active" : ""}`}
            style={{ "--card-color": item.color }}
            onClick={() => item.key !== "total" && applyFilter({ severity: activeFilter.severity === item.key ? "" : item.key })}
          >
            <div className="severity-count" style={{ color: item.color }}>{item.count || 0}</div>
            <div className="severity-label">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="scan-tabs">
        {["overview", "findings", "categories", "sources"].map((tab) => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "findings" && findings.length > 0 && (
              <span className="tab-count">{findings.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {/* Overview */}
        {activeTab === "overview" && (
          <div className="overview-grid animate-in">
            {/* Severity chart */}
            <div className="card chart-card">
              <div className="card-header"><h3>Severity Distribution</h3></div>
              <div className="card-body">
                {SEVERITY_ORDER.map((sev) => {
                  const count = severityData[sev] || 0;
                  const total = stats?.total || 1;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <div key={sev} className="bar-row">
                      <span className="bar-label mono">{sev}</span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{ width: `${pct}%`, background: SEVERITY_COLORS[sev] }}
                        />
                      </div>
                      <span className="bar-count">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Category breakdown */}
            <div className="card chart-card">
              <div className="card-header"><h3>Exposure Categories</h3></div>
              <div className="card-body">
                {Object.entries(categoryData)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 8)
                  .map(([cat, count]) => (
                    <div key={cat} className="cat-row" onClick={() => applyFilter({ category: cat })}>
                      <span className="cat-label">{CATEGORY_LABELS[cat] || cat}</span>
                      <span className="cat-count">{count}</span>
                    </div>
                  ))}
                {Object.keys(categoryData).length === 0 && (
                  <div className="empty-state" style={{ padding: "20px" }}>
                    <div className="empty-state-desc">No data yet</div>
                  </div>
                )}
              </div>
            </div>

            {/* Scan info */}
            <div className="card info-card">
              <div className="card-header"><h3>Scan Information</h3></div>
              <div className="card-body">
                <div className="info-row">
                  <span className="info-key">Domain</span>
                  <span className="info-val mono">{scan.domain}</span>
                </div>
                <div className="info-row">
                  <span className="info-key">Status</span>
                  <span className={`badge ${scan.status}`}>{scan.status}</span>
                </div>
                <div className="info-row">
                  <span className="info-key">Dorks Executed</span>
                  <span className="info-val mono">{scan.dorks_executed} / {scan.dorks_total || "?"}</span>
                </div>
                <div className="info-row">
                  <span className="info-key">AI Analysis</span>
                  <span className="info-val">{scan.scan_config?.has_openai ? "✓ OpenAI" : "Rule-based"}</span>
                </div>
                <div className="info-row">
                  <span className="info-key">GitHub Scan</span>
                  <span className="info-val">{scan.scan_config?.has_github ? "✓ With token" : "Web-based"}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Findings List */}
        {activeTab === "findings" && (
          <div className="findings-section animate-in">
            {/* Filter bar */}
            <div className="filter-bar">
              <div className="filter-group">
                <span className="filter-label">Severity:</span>
                {["critical", "high", "medium", "low", "info"].map((s) => (
                  <button
                    key={s}
                    className={`filter-chip ${activeFilter.severity === s ? "active" : ""}`}
                    onClick={() => applyFilter({ severity: activeFilter.severity === s ? "" : s })}
                  >
                    <span className="badge" style={{ background: "none", border: "none", padding: "0" }}>
                      {s}
                    </span>
                  </button>
                ))}
              </div>
              {(activeFilter.severity || activeFilter.category || activeFilter.source) && (
                <button className="btn btn-ghost btn-sm" onClick={() => applyFilter({ severity: "", category: "", source: "" })}>
                  Clear filters
                </button>
              )}
            </div>

            {/* Findings table */}
            {findings.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">◈</div>
                <div className="empty-state-title">
                  {isRunning ? "Scanning in progress..." : "No findings found"}
                </div>
                <div className="empty-state-desc">
                  {isRunning ? "Results will appear as scan progresses" : "Try adjusting your filters"}
                </div>
              </div>
            ) : (
              <div className="findings-list">
                {findings.map((f) => (
                  <div
                    key={f.id}
                    className={`finding-row ${selectedFinding?.id === f.id ? "expanded" : ""}`}
                    onClick={() => setSelectedFinding(selectedFinding?.id === f.id ? null : f)}
                  >
                    <div className="finding-main">
                      <span className={`badge ${f.severity}`}>{f.severity}</span>
                      <div className="finding-url-group">
                        <span className="finding-url mono">{truncateUrl(f.url, 70)}</span>
                        {f.title && <span className="finding-title">{f.title.slice(0, 80)}</span>}
                      </div>
                      <span className="finding-source">
                        {SOURCE_LABELS[f.source] || f.source}
                      </span>
                      <span className="finding-category">{CATEGORY_LABELS[f.category] || f.category}</span>
                      <span className="finding-expand">{selectedFinding?.id === f.id ? "▲" : "▼"}</span>
                    </div>

                    {selectedFinding?.id === f.id && (
                      <div className="finding-detail animate-in">
                        <div className="detail-row">
                          <span className="detail-key">Full URL</span>
                          <a href={f.url} target="_blank" rel="noopener noreferrer" className="detail-url mono">
                            {f.url}
                          </a>
                        </div>
                        <div className="detail-row">
                          <span className="detail-key">Dork Query</span>
                          <code className="detail-code">{f.dork_query}</code>
                        </div>
                        {f.snippet && (
                          <div className="detail-row">
                            <span className="detail-key">Snippet</span>
                            <span className="detail-snippet">{f.snippet}</span>
                          </div>
                        )}
                        {f.ai_explanation && (
                          <div className="detail-row ai-analysis">
                            <span className="detail-key">⬡ AI Analysis</span>
                            <span className="detail-ai-text">{f.ai_explanation}</span>
                          </div>
                        )}
                        <div className="detail-row">
                          <span className="detail-key">Discovered</span>
                          <span className="mono" style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                            {formatDate(f.discovered_at)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Categories */}
        {activeTab === "categories" && (
          <div className="categories-grid animate-in">
            {Object.entries(CATEGORY_LABELS).map(([catKey, catLabel]) => {
              const count = categoryData[catKey] || 0;
              return (
                <div
                  key={catKey}
                  className={`category-card ${count > 0 ? "has-findings" : "empty"}`}
                  onClick={() => count > 0 && (setActiveTab("findings"), applyFilter({ category: catKey }))}
                >
                  <div className="cat-card-count" style={{ color: count > 0 ? "var(--accent-primary)" : "var(--text-tertiary)" }}>
                    {count}
                  </div>
                  <div className="cat-card-label">{catLabel}</div>
                  {count > 0 && <span className="cat-card-arrow">→</span>}
                </div>
              );
            })}
          </div>
        )}

        {/* Sources */}
        {activeTab === "sources" && (
          <div className="sources-section animate-in">
            {Object.entries(stats?.source_distribution || {}).length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">◎</div>
                <div className="empty-state-title">No source data yet</div>
              </div>
            ) : (
              <div className="sources-grid">
                {Object.entries(stats?.source_distribution || {}).map(([src, count]) => (
                  <div key={src} className="source-card">
                    <div className="source-count">{count}</div>
                    <div className="source-label">{SOURCE_LABELS[src] || src}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Selected finding drawer */}
    </div>
  );
}
