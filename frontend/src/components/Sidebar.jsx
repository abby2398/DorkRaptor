import { useState } from "react";
import { clearAuth, isAdmin } from "../utils/auth";
import "./Sidebar.css";

export default function Sidebar({ currentPage, onNavigate, isOpen, onToggle, user }) {
  const admin = isAdmin();

  const NAV_ITEMS = [
    { id: "dashboard", label: "Dashboard", icon: "⬡" },
    { id: "history", label: "Scan History", icon: "◈" },
    { id: "settings", label: "Settings", icon: "◎" },
    ...(admin ? [{ id: "admin", label: "Admin Panel", icon: "🛡", adminOnly: true }] : []),
  ];

  const handleLogout = () => {
    clearAuth();
    window.location.reload();
  };

  return (
    <aside className={`sidebar ${isOpen ? "open" : "closed"}`}>
      <div className="sidebar-logo" onClick={onToggle}>
        <div className="logo-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" stroke="#00ff9d" strokeWidth="1.5" fill="rgba(0,255,157,0.05)"/>
            <polygon points="14,7 21,11 21,17 14,21 7,17 7,11" stroke="#00ff9d" strokeWidth="1" fill="rgba(0,255,157,0.1)"/>
            <circle cx="14" cy="14" r="3" fill="#00ff9d"/>
          </svg>
        </div>
        {isOpen && (
          <div className="logo-text">
            <span className="logo-name">DorkRaptor</span>
            <span className="logo-tagline">OSINT Platform</span>
          </div>
        )}
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentPage === item.id || (currentPage === "scan" && item.id === "dashboard") ? "active" : ""} ${item.adminOnly ? "admin-nav-item" : ""}`}
            onClick={() => onNavigate(item.id)}
            title={!isOpen ? item.label : undefined}
          >
            <span className="nav-icon">{item.icon}</span>
            {isOpen && <span className="nav-label">{item.label}</span>}
            {currentPage === item.id && <span className="nav-indicator" />}
          </button>
        ))}
      </nav>

      {/* User Info */}
      {isOpen && user && (
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            {user.avatar_url
              ? <img src={user.avatar_url} alt="" />
              : <span>{(user.full_name || user.email)[0].toUpperCase()}</span>
            }
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.full_name || user.email.split("@")[0]}</div>
            <div className="sidebar-user-role">{user.role === "admin" ? "🛡 Admin" : "User"}</div>
          </div>
          <button className="sidebar-logout" onClick={handleLogout} title="Sign out">⏻</button>
        </div>
      )}

      {!isOpen && user && (
        <button className="nav-item" onClick={handleLogout} title="Sign out" style={{ marginTop: "auto" }}>
          <span className="nav-icon">⏻</span>
        </button>
      )}

      {isOpen && (
        <div className="sidebar-footer">
          <div className="version-tag">v1.0.0</div>
          <div className="disclaimer">For authorized use only</div>
        </div>
      )}
    </aside>
  );
}
