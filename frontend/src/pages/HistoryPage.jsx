import { useState, useEffect } from "react";
import { api, formatDate } from "../utils/api";
import "./HistoryPage.css";

export default function HistoryPage({ onNavigate }) {
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => { loadScans(); }, []);

  const loadScans = async () => {
    try {
      const data = await api.listScans(0, 50);
      setScans(data);
    } catch (e) {}
    setLoading(false);
  };

  const deleteScan = async (e, id) => {
    e.stopPropagation();
    if (!confirm("Delete this scan and all its findings?")) return;
    setDeletingId(id);
    try {
      await api.deleteScan(id);
      setScans((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      alert("Failed to delete scan");
    }
    setDeletingId(null);
  };

  const getDuration = (scan) => {
    if (!scan.started_at || !scan.completed_at) return "—";
    const ms = new Date(scan.completed_at) - new Date(scan.started_at);
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  if (loading) {
    return (
      <div className="page history-page">
        <div style={{ display: "flex", justifyContent: "center", padding: "80px", color: "var(--text-tertiary)" }}>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="page history-page animate-in">
      <div className="page-header">
        <h1 className="page-title">Scan History</h1>
        <p className="page-subtitle">{scans.length} total scans recorded</p>
      </div>

      {scans.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">◈</div>
          <div className="empty-state-title">No scans yet</div>
          <div className="empty-state-desc">Run your first reconnaissance scan from the dashboard</div>
          <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={() => onNavigate("dashboard")}>
            Start Scanning
          </button>
        </div>
      ) : (
        <div className="history-table">
          <div className="table-header">
            <span>Domain</span>
            <span>Status</span>
            <span>Findings</span>
            <span>Critical</span>
            <span>High</span>
            <span>Duration</span>
            <span>Date</span>
            <span></span>
          </div>
          {scans.map((scan) => (
            <div
              key={scan.id}
              className="table-row"
              onClick={() => onNavigate("scan", scan.id)}
            >
              <span className="td-domain mono">{scan.domain}</span>
              <span>
                <span className={`badge ${scan.status}`}>
                  <span className={`status-dot ${scan.status}`} />
                  {scan.status}
                </span>
              </span>
              <span className="td-number">{scan.total_findings || 0}</span>
              <span className="td-number critical">{scan.critical_count || 0}</span>
              <span className="td-number high">{scan.high_count || 0}</span>
              <span className="td-meta mono">{getDuration(scan)}</span>
              <span className="td-meta mono">{formatDate(scan.created_at)}</span>
              <span>
                <button
                  className="btn btn-danger btn-sm"
                  disabled={deletingId === scan.id}
                  onClick={(e) => deleteScan(e, scan.id)}
                  style={{ padding: "4px 10px", fontSize: 11 }}
                >
                  {deletingId === scan.id ? "..." : "Delete"}
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
