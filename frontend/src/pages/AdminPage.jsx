import { useState, useEffect } from "react";
import { api, formatDate } from "../utils/api";
import "./AdminPage.css";

const TABS = ["overview", "users", "scans"];

export default function AdminPage({ onNavigate }) {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [scans, setScans] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [totalScans, setTotalScans] = useState(0);
  const [loading, setLoading] = useState(true);

  // User modal state
  const [userModal, setUserModal] = useState(null); // null | "create" | user object
  const [userForm, setUserForm] = useState({ email: "", password: "", full_name: "", role: "user" });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, u, sc] = await Promise.all([
        api.adminStats(),
        api.adminListUsers(),
        api.adminListScans(),
      ]);
      setStats(s);
      setUsers(u.users);
      setTotalUsers(u.total);
      setScans(sc.scans);
      setTotalScans(sc.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openCreateUser = () => {
    setUserForm({ email: "", password: "", full_name: "", role: "user" });
    setFormError("");
    setUserModal("create");
  };

  const openEditUser = (u) => {
    setUserForm({ email: u.email, password: "", full_name: u.full_name || "", role: u.role });
    setFormError("");
    setUserModal(u);
  };

  const saveUser = async () => {
    setFormError("");
    setSaving(true);
    try {
      if (userModal === "create") {
        if (!userForm.email || !userForm.password) { setFormError("Email and password required"); setSaving(false); return; }
        await api.adminCreateUser(userForm);
      } else {
        const patch = {};
        if (userForm.full_name !== userModal.full_name) patch.full_name = userForm.full_name;
        if (userForm.role !== userModal.role) patch.role = userForm.role;
        if (userForm.password) patch.password = userForm.password;
        await api.adminUpdateUser(userModal.id, patch);
      }
      setUserModal(null);
      await loadData();
    } catch (e) {
      setFormError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const deleteUser = async (u) => {
    if (!confirm(`Delete user ${u.email}? This cannot be undone.`)) return;
    try {
      await api.adminDeleteUser(u.id);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const deleteScan = async (id) => {
    if (!confirm("Delete this scan and all findings?")) return;
    try {
      await api.adminDeleteScan(id);
      await loadData();
    } catch (e) {
      alert(e.message);
    }
  };

  const toggleActive = async (u) => {
    try {
      await api.adminUpdateUser(u.id, { is_active: !u.is_active });
      await loadData();
    } catch (e) { alert(e.message); }
  };

  if (loading) return (
    <div className="page admin-page">
      <div className="loading-center"><div className="spinner" style={{ width: 32, height: 32 }} /><p>Loading admin panel...</p></div>
    </div>
  );

  return (
    <div className="page admin-page animate-in">
      {/* Header */}
      <div className="admin-header">
        <div>
          <h1 className="admin-title">⬡ Admin Panel</h1>
          <p className="admin-subtitle">Manage users, scans, and platform data</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        {TABS.map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === "overview" && stats && (
        <div className="admin-overview animate-in">
          <div className="admin-stats-grid">
            {[
              { label: "Total Users", value: stats.total_users, icon: "👥", color: "var(--accent-blue)" },
              { label: "Total Scans", value: stats.total_scans, icon: "🔍", color: "var(--accent-primary)" },
              { label: "Active Scans", value: stats.active_scans, icon: "⚡", color: "var(--severity-medium)" },
              { label: "Total Findings", value: stats.total_findings, icon: "◈", color: "var(--accent-purple)" },
              { label: "Critical Findings", value: stats.critical_findings, icon: "⚠", color: "var(--severity-critical)" },
            ].map((s) => (
              <div key={s.label} className="admin-stat-card">
                <div className="admin-stat-icon">{s.icon}</div>
                <div className="admin-stat-value" style={{ color: s.color }}>{s.value}</div>
                <div className="admin-stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="admin-quick-tables">
            <div className="card">
              <div className="card-header"><h3>Recent Users</h3></div>
              <div className="card-body">
                {users.slice(0, 5).map((u) => (
                  <div key={u.id} className="admin-row">
                    <div className="admin-user-avatar">{(u.full_name || u.email)[0].toUpperCase()}</div>
                    <div className="admin-row-info">
                      <div className="admin-row-name">{u.full_name || "—"}</div>
                      <div className="admin-row-sub">{u.email}</div>
                    </div>
                    <span className={`badge ${u.role === "admin" ? "critical" : "info"}`}>{u.role}</span>
                    <span className={`status-dot ${u.is_active ? "completed" : "failed"}`} />
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h3>Recent Scans</h3></div>
              <div className="card-body">
                {scans.slice(0, 5).map((s) => (
                  <div key={s.id} className="admin-row" style={{ cursor: "pointer" }} onClick={() => onNavigate("scan", s.id)}>
                    <span className={`status-dot ${s.status}`} />
                    <div className="admin-row-info">
                      <div className="admin-row-name mono">{s.domain}</div>
                      <div className="admin-row-sub">{formatDate(s.created_at)}</div>
                    </div>
                    <span className="badge info">{s.total_findings} findings</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Users */}
      {tab === "users" && (
        <div className="admin-section animate-in">
          <div className="section-header">
            <h2>Users <span className="section-count">({totalUsers})</span></h2>
            <button className="btn btn-primary btn-sm" onClick={openCreateUser}>+ Add User</button>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="user-cell">
                        <div className="admin-user-avatar sm">{(u.full_name || u.email)[0].toUpperCase()}</div>
                        <span>{u.full_name || "—"}</span>
                      </div>
                    </td>
                    <td className="mono">{u.email}</td>
                    <td><span className={`badge ${u.role === "admin" ? "critical" : "info"}`}>{u.role}</span></td>
                    <td><span className="badge medium">{u.provider}</span></td>
                    <td>
                      <span className={`status-badge ${u.is_active ? "active" : "inactive"}`}>
                        {u.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="mono text-sm">{formatDate(u.created_at)}</td>
                    <td>
                      <div className="action-btns">
                        <button className="btn btn-ghost btn-xs" onClick={() => openEditUser(u)}>Edit</button>
                        <button className="btn btn-ghost btn-xs" onClick={() => toggleActive(u)}>
                          {u.is_active ? "Disable" : "Enable"}
                        </button>
                        <button className="btn btn-danger btn-xs" onClick={() => deleteUser(u)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scans */}
      {tab === "scans" && (
        <div className="admin-section animate-in">
          <div className="section-header">
            <h2>All Scans <span className="section-count">({totalScans})</span></h2>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Findings</th>
                  <th>Critical</th>
                  <th>High</th>
                  <th>Started</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.id}>
                    <td className="mono">{s.domain}</td>
                    <td><span className={`badge ${s.status}`}><span className={`status-dot ${s.status}`} />{s.status}</span></td>
                    <td>{s.total_findings}</td>
                    <td><span style={{ color: "var(--severity-critical)", fontWeight: 700 }}>{s.critical_count || 0}</span></td>
                    <td><span style={{ color: "var(--severity-high)", fontWeight: 700 }}>{s.high_count || 0}</span></td>
                    <td className="mono text-sm">{formatDate(s.created_at)}</td>
                    <td>
                      <div className="action-btns">
                        <button className="btn btn-ghost btn-xs" onClick={() => onNavigate("scan", s.id)}>View</button>
                        <button className="btn btn-danger btn-xs" onClick={() => deleteScan(s.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* User Modal */}
      {userModal && (
        <div className="modal-overlay" onClick={() => setUserModal(null)}>
          <div className="modal-box animate-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{userModal === "create" ? "Add New User" : `Edit: ${userModal.email}`}</h3>
              <button className="modal-close" onClick={() => setUserModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              {userModal === "create" && (
                <div className="auth-field">
                  <label>Email *</label>
                  <input type="email" className="input-field" value={userForm.email}
                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} />
                </div>
              )}
              <div className="auth-field">
                <label>Full Name</label>
                <input type="text" className="input-field" value={userForm.full_name}
                  onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })} />
              </div>
              <div className="auth-field">
                <label>{userModal === "create" ? "Password *" : "New Password (leave blank to keep)"}</label>
                <input type="password" className="input-field" value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} />
              </div>
              <div className="auth-field">
                <label>Role</label>
                <select className="input-field" value={userForm.role}
                  onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              {formError && <div className="auth-error">{formError}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setUserModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={saveUser} disabled={saving}>
                {saving ? <><span className="spinner" /> Saving...</> : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
