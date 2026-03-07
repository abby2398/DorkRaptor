import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../utils/api";
import "./NotificationSystem.css";

/**
 * Polls active scans and fires a browser notification + in-app toast
 * when a scan transitions to "completed" or "failed".
 */
export default function NotificationSystem() {
  const [toasts, setToasts] = useState([]);
  const watchedRef = useRef({}); // { scanId: lastStatus }
  const pollRef = useRef(null);

  const addToast = useCallback((toast) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 7000);
  }, []);

  const fireNotification = useCallback((scan, type) => {
    const title = type === "completed"
      ? `✅ Scan complete: ${scan.domain}`
      : `❌ Scan failed: ${scan.domain}`;
    const body = type === "completed"
      ? `Found ${scan.total_findings} findings (${scan.critical_count} critical)`
      : scan.error_message || "Scan encountered an error";

    // Browser notification
    if (Notification.permission === "granted") {
      new Notification(title, { body, icon: "/favicon.svg" });
    }

    // In-app toast
    addToast({ type, title, body, scanId: scan.id, domain: scan.domain });
  }, [addToast]);

  const requestPermission = () => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  };

  useEffect(() => {
    requestPermission();

    const poll = async () => {
      try {
        const scans = await api.listScans(0, 20);
        scans.forEach((scan) => {
          const prev = watchedRef.current[scan.id];
          const curr = scan.status;

          // First time seeing it while running — track it
          if (!prev && (curr === "running" || curr === "pending")) {
            watchedRef.current[scan.id] = curr;
            return;
          }

          // Already tracked — check for terminal transition
          if (prev && prev !== "completed" && prev !== "failed") {
            if (curr === "completed" || curr === "failed") {
              fireNotification(scan, curr);
            }
          }

          watchedRef.current[scan.id] = curr;
        });
      } catch { /* silent */ }
    };

    pollRef.current = setInterval(poll, 5000);
    return () => clearInterval(pollRef.current);
  }, [fireNotification]);

  const dismissToast = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type} animate-in`}>
          <div className="toast-icon">{t.type === "completed" ? "✅" : "❌"}</div>
          <div className="toast-content">
            <div className="toast-title">{t.title}</div>
            <div className="toast-body">{t.body}</div>
          </div>
          <button className="toast-dismiss" onClick={() => dismissToast(t.id)}>✕</button>
        </div>
      ))}
    </div>
  );
}
