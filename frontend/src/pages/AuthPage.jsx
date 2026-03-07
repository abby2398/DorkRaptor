import { useState } from "react";
import { api } from "../utils/api";
import { setAuth } from "../utils/auth";
import "./AuthPage.css";

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  const handleSubmit = async () => {
    setError("");
    if (!form.email || !form.password) { setError("Email and password required"); return; }
    setLoading(true);
    try {
      const res = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register({ email: form.email, password: form.password, full_name: form.full_name });
      setAuth(res.access_token, res.user);
      onAuth(res.user);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    if (!GOOGLE_CLIENT_ID) {
      setError("Google Sign-In is not configured (set VITE_GOOGLE_CLIENT_ID).");
      return;
    }
    // Load Google GSI if not loaded
    if (!window.google) {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.onload = initGSI;
      document.body.appendChild(script);
    } else {
      initGSI();
    }
  };

  const initGSI = () => {
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async ({ credential }) => {
        setLoading(true);
        setError("");
        try {
          const res = await api.googleAuth(credential);
          setAuth(res.access_token, res.user);
          onAuth(res.user);
        } catch (e) {
          setError(e.message);
        } finally {
          setLoading(false);
        }
      },
    });
    window.google.accounts.id.prompt();
  };

  return (
    <div className="auth-shell scanline-bg">
      <div className="auth-card animate-in">
        {/* Logo */}
        <div className="auth-logo">
          <svg width="36" height="36" viewBox="0 0 28 28" fill="none">
            <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" stroke="#00ff9d" strokeWidth="1.5" fill="rgba(0,255,157,0.05)"/>
            <polygon points="14,7 21,11 21,17 14,21 7,17 7,11" stroke="#00ff9d" strokeWidth="1" fill="rgba(0,255,157,0.1)"/>
            <circle cx="14" cy="14" r="3" fill="#00ff9d"/>
          </svg>
          <div>
            <div className="auth-brand">DorkRaptor</div>
            <div className="auth-tagline">OSINT Intelligence Platform</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="auth-tabs">
          <button className={`auth-tab ${mode === "login" ? "active" : ""}`} onClick={() => { setMode("login"); setError(""); }}>
            Sign In
          </button>
          <button className={`auth-tab ${mode === "register" ? "active" : ""}`} onClick={() => { setMode("register"); setError(""); }}>
            Register
          </button>
        </div>

        {/* Form */}
        <div className="auth-form">
          {mode === "register" && (
            <div className="auth-field">
              <label>Full Name <span className="optional">(optional)</span></label>
              <input
                type="text"
                className="input-field"
                placeholder="John Doe"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
          )}
          <div className="auth-field">
            <label>Email</label>
            <input
              type="email"
              className="input-field"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>
          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              className="input-field"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button className="btn btn-primary auth-submit-btn" onClick={handleSubmit} disabled={loading}>
            {loading ? <><span className="spinner" /> Loading...</> : mode === "login" ? "Sign In" : "Create Account"}
          </button>

          <div className="auth-divider"><span>or</span></div>

          <button className="btn btn-google" onClick={handleGoogle} disabled={loading}>
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Continue with Google
          </button>
        </div>

        {mode === "register" && (
          <p className="auth-note">First registered account gets admin privileges.</p>
        )}
      </div>
    </div>
  );
}
