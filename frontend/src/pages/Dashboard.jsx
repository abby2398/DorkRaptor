import { useState, useEffect } from "react";
import { api, formatDate, SEVERITY_COLORS } from "../utils/api";
import "./Dashboard.css";

export default function Dashboard({ onNavigate }) {
  const [domain, setDomain] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState(null);
  const [recentScans, setRecentScans] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [healthInfo, setHealthInfo] = useState(null);

  useEffect(() => {
    loadRecentScans();
    loadHealth();
  }, []);

  const loadRecentScans = async () => {
    try {
      const scans = await api.listScans(0, 5);
      setRecentScans(scans);
    } catch (e) {
      console.warn("Could not load scans:", e);
    }
  };

  const loadHealth = async () => {
    try {
      const h = await api.health();
      setHealthInfo(h);
    } catch (e) {}
  };

  const startScan = async () => {
    if (!domain.trim()) {
      setError("Please enter a domain to scan");
      return;
    }
    setError(null);
    setScanning(true);
    try {
      const scan = await api.createScan({
        domain: domain.trim(),
        openai_key: openaiKey || undefined,
        github_token: githubToken || undefined,
      });
      onNavigate("scan", scan.id);
    } catch (e) {
      setError(e.message || "Failed to start scan");
      setScanning(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") startScan();
  };

  const totalFindings = recentScans.reduce((s, sc) => s + (sc.total_findings || 0), 0);
  const criticalTotal = recentScans.reduce((s, sc) => s + (sc.critical_count || 0), 0);

  return (
    <div className="page dashboard-page scanline-bg">
      {/* Hero section */}
      <div className="hero-section animate-in">
        <div className="hero-label">
          <span className="status-dot running" />
          <span>OSINT Intelligence Platform</span>
        </div>
        <h1 className="hero-title">
          <span className="title-raptor">DORK</span>
          <span className="title-accent">RAPTOR</span>
        </h1>
        <p className="hero-subtitle">
          Automated Google dorking, OSINT discovery, and threat intelligence for any domain
        </p>

        {/* Scan Input */}
        <div className="scan-input-container">
          <div className="scan-input-wrapper">
            <div className="scan-icon">⬡</div>
            <input
              type="text"
              className="scan-domain-input"
              placeholder="example.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={scanning}
              autoFocus
            />
            <button
              className="btn btn-primary scan-btn"
              onClick={startScan}
              disabled={scanning || !domain.trim()}
            >
              {scanning ? (
                <>
                  <span className="spinner" />
                  Initializing...
                </>
              ) : (
                <>
                  <span>▶</span>
                  Launch Scan
                </>
              )}
            </button>
          </div>

          {error && <div className="scan-error">{error}</div>}

          {/* Advanced Options */}
          <div className="advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
            <span>{showAdvanced ? "▲" : "▼"}</span>
            Advanced Options
          </div>

          {showAdvanced && (
            <div className="advanced-panel animate-in">
              <div className="advanced-row">
                <div className="advanced-field">
                  <label>OpenAI API Key <span className="optional">(for AI analysis)</span></label>
                  <input
                    type="password"
                    className="input-field"
                    placeholder="sk-..."
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                  />
                </div>
                <div className="advanced-field">
                  <label>GitHub Token <span className="optional">(for leak detection)</span></label>
                  <input
                    type="password"
                    className="input-field"
                    placeholder="ghp_..."
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                  />
                </div>
              </div>
              <p className="advanced-note">Keys are sent directly to scan APIs and never stored on server.</p>
            </div>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="stats-grid animate-in" style={{ animationDelay: "0.1s" }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ color: "var(--accent-primary)" }}>◈</div>
          <div className="stat-value">{healthInfo?.dork_database_size || "300+"}</div>
          <div className="stat-label">Dork Database</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ color: "var(--accent-blue)" }}>⬡</div>
          <div className="stat-value">{recentScans.length}</div>
          <div className="stat-label">Scans Run</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ color: "var(--severity-medium)" }}>◎</div>
          <div className="stat-value">{totalFindings}</div>
          <div className="stat-label">Total Findings</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ color: "var(--severity-critical)" }}>⚠</div>
          <div className="stat-value">{criticalTotal}</div>
          <div className="stat-label">Critical Issues</div>
        </div>
      </div>

      {/* Feature cards */}
      <div className="features-grid animate-in" style={{ animationDelay: "0.15s" }}>
        <div className="feature-card">
          <div className="feature-icon">🔍</div>
          <h3>Google Dorking</h3>
          <p>300+ categorized dorks across 12 threat categories, executed across multiple search engines</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🐙</div>
          <h3>GitHub Leaks</h3>
          <p>Scans GitHub repositories for exposed credentials, API keys, and sensitive configuration files</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">☁️</div>
          <h3>Cloud Exposure</h3>
          <p>Discovers exposed S3 buckets, Azure Storage, and Google Cloud endpoints related to your target</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🤖</div>
          <h3>AI Analysis</h3>
          <p>OpenAI-powered risk classification and natural language explanations for every finding</p>
        </div>
      </div>

      {/* Recent Scans */}
      {recentScans.length > 0 && (
        <div className="recent-section animate-in" style={{ animationDelay: "0.2s" }}>
          <div className="section-header">
            <h2>Recent Scans</h2>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("history")}>
              View All →
            </button>
          </div>
          <div className="recent-list">
            {recentScans.map((scan) => (
              <div
                key={scan.id}
                className="recent-scan-row"
                onClick={() => onNavigate("scan", scan.id)}
              >
                <span className={`status-dot ${scan.status}`} />
                <span className="scan-domain-text">{scan.domain}</span>
                <span className="scan-meta">{formatDate(scan.created_at)}</span>
                <div className="scan-counts">
                  {scan.critical_count > 0 && (
                    <span className="badge critical">{scan.critical_count}</span>
                  )}
                  {scan.high_count > 0 && (
                    <span className="badge high">{scan.high_count}</span>
                  )}
                  {scan.medium_count > 0 && (
                    <span className="badge medium">{scan.medium_count}</span>
                  )}
                </div>
                <span className="scan-total">{scan.total_findings} findings</span>
                <span className="scan-arrow">→</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
