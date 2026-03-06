import { useState, useEffect } from "react";
import { api } from "../utils/api";
import "./SettingsPage.css";

export default function SettingsPage() {
  const [openaiKey, setOpenaiKey] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [searchDelayMin, setSearchDelayMin] = useState(2.0);
  const [searchDelayMax, setSearchDelayMax] = useState(5.0);
  const [savedMsg, setSavedMsg] = useState("");
  const [currentSettings, setCurrentSettings] = useState(null);

  useEffect(() => { loadSettings(); }, []);

  const loadSettings = async () => {
    try {
      const s = await api.getSettings();
      setCurrentSettings(s);
      setSearchDelayMin(s.search_delay_min);
      setSearchDelayMax(s.search_delay_max);
    } catch (e) {}
  };

  const saveSettings = async () => {
    try {
      await api.updateSettings({
        openai_api_key: openaiKey || undefined,
        github_token: githubToken || undefined,
        search_delay_min: searchDelayMin,
        search_delay_max: searchDelayMax,
      });
      setSavedMsg("Settings saved successfully");
      loadSettings();
      setTimeout(() => setSavedMsg(""), 3000);
    } catch (e) {
      setSavedMsg("Failed to save settings");
    }
  };

  return (
    <div className="page settings-page animate-in">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure API keys and scan behavior</p>
      </div>

      <div className="settings-layout">
        {/* API Keys */}
        <div className="settings-section card">
          <div className="card-header">
            <h3>API Keys</h3>
          </div>
          <div className="settings-body">
            <div className="setting-field">
              <label>OpenAI API Key</label>
              <p className="setting-desc">Enables AI-powered vulnerability analysis and explanations. Without this, rule-based classification is used.</p>
              <div className="key-status">
                {currentSettings?.openai_configured ? (
                  <span className="configured-badge">✓ Configured</span>
                ) : (
                  <span className="not-configured">Not configured</span>
                )}
              </div>
              <input
                type="password"
                className="input-field"
                placeholder="sk-..."
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
              />
            </div>

            <div className="setting-field">
              <label>GitHub Personal Access Token</label>
              <p className="setting-desc">Enables GitHub API access for more thorough leak detection. Without this, web search is used.</p>
              <div className="key-status">
                {currentSettings?.github_configured ? (
                  <span className="configured-badge">✓ Configured</span>
                ) : (
                  <span className="not-configured">Not configured</span>
                )}
              </div>
              <input
                type="password"
                className="input-field"
                placeholder="ghp_..."
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Scan Behavior */}
        <div className="settings-section card">
          <div className="card-header">
            <h3>Scan Behavior</h3>
          </div>
          <div className="settings-body">
            <div className="setting-field">
              <label>Search Delay (seconds)</label>
              <p className="setting-desc">Random delay between requests to avoid rate limiting. Higher values are safer but slower.</p>
              <div className="range-row">
                <div className="range-item">
                  <span>Min</span>
                  <input
                    type="number"
                    className="input-field"
                    min="1" max="10" step="0.5"
                    value={searchDelayMin}
                    onChange={(e) => setSearchDelayMin(parseFloat(e.target.value))}
                    style={{ width: 100 }}
                  />
                </div>
                <div className="range-item">
                  <span>Max</span>
                  <input
                    type="number"
                    className="input-field"
                    min="1" max="30" step="0.5"
                    value={searchDelayMax}
                    onChange={(e) => setSearchDelayMax(parseFloat(e.target.value))}
                    style={{ width: 100 }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Ethical Use */}
        <div className="settings-section card ethics-card">
          <div className="card-header">
            <h3>⚠ Ethical Use Policy</h3>
          </div>
          <div className="settings-body">
            <p>DorkRaptor is designed for authorized security testing, research, and vulnerability disclosure. By using this tool you agree to:</p>
            <ul>
              <li>Only scan domains you own or have explicit written permission to test</li>
              <li>Not use findings to exploit systems or access unauthorized data</li>
              <li>Report discovered vulnerabilities responsibly to asset owners</li>
              <li>Comply with applicable laws including the CFAA and local equivalents</li>
            </ul>
            <p className="ethics-note">This tool only uses publicly indexed information. It does not perform active exploitation.</p>
          </div>
        </div>

        <div className="settings-actions">
          {savedMsg && <span className={`save-msg ${savedMsg.includes("Failed") ? "error" : "success"}`}>{savedMsg}</span>}
          <button className="btn btn-primary" onClick={saveSettings}>Save Settings</button>
        </div>
      </div>
    </div>
  );
}
