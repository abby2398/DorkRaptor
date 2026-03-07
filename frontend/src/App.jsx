import { useState, useEffect } from "react";
import { getUser, getToken } from "./utils/auth";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import ScanPage from "./pages/ScanPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";
import AdminPage from "./pages/AdminPage";
import Sidebar from "./components/Sidebar";
import NotificationSystem from "./components/NotificationSystem";
import "./styles/globals.css";

export default function App() {
  const [user, setUser] = useState(getUser());
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [activeScanId, setActiveScanId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Keep user in sync with token
  useEffect(() => {
    if (!getToken()) setUser(null);
  }, []);

  const handleAuth = (u) => setUser(u);

  const navigateTo = (page, scanId = null) => {
    setCurrentPage(page);
    if (scanId) setActiveScanId(scanId);
  };

  if (!user) {
    return <AuthPage onAuth={handleAuth} />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard": return <Dashboard onNavigate={navigateTo} />;
      case "scan": return <ScanPage scanId={activeScanId} onNavigate={navigateTo} />;
      case "history": return <HistoryPage onNavigate={navigateTo} />;
      case "settings": return <SettingsPage />;
      case "admin": return <AdminPage onNavigate={navigateTo} />;
      default: return <Dashboard onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        currentPage={currentPage}
        onNavigate={navigateTo}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        user={user}
      />
      <main className={`main-content ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
        {renderPage()}
      </main>
      <NotificationSystem />
    </div>
  );
}
