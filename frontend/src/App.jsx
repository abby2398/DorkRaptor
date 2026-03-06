import { useState, useEffect } from "react";
import Dashboard from "./pages/Dashboard";
import ScanPage from "./pages/ScanPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";
import Sidebar from "./components/Sidebar";
import "./styles/globals.css";

export default function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [activeScanId, setActiveScanId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navigateTo = (page, scanId = null) => {
    setCurrentPage(page);
    if (scanId) setActiveScanId(scanId);
  };

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return <Dashboard onNavigate={navigateTo} />;
      case "scan":
        return <ScanPage scanId={activeScanId} onNavigate={navigateTo} />;
      case "history":
        return <HistoryPage onNavigate={navigateTo} />;
      case "settings":
        return <SettingsPage />;
      default:
        return <Dashboard onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        currentPage={currentPage}
        onNavigate={navigateTo}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <main className={`main-content ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
        {renderPage()}
      </main>
    </div>
  );
}
