import React, { useState } from "react";
import { api, setToken } from "../api/client.js";

export default function Register({ onRegistered, switchToLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      // Adjust this method name if your client.js uses a different sign-up method name (e.g., api.register)
      await api.register(email, password);
      
      // Automatically log in after successful registration or prompt them
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onRegistered();
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="bbox-card login-card" onSubmit={handleSubmit}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <div className="page-eyebrow">Pedestrian Detection System</div>
        <h1 style={{ marginBottom: 24 }}>Officer Registration</h1>

        <div className="field">
          <label htmlFor="email">Official Email</label>
          <input
            id="email"
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="officer@pedespi.local"
            required
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </div>

        <div className="field">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input
            id="confirmPassword"
            className="input"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </div>

        {error && <div className="error-text" style={{ color: "#ff4d4d", marginBottom: 12, fontSize: "0.875rem" }}>{error}</div>}

        <button className="btn" type="submit" disabled={loading} style={{ width: "100%", marginTop: 8 }}>
          {loading ? "Initializing clearance…" : "Create Account"}
        </button>

        {switchToLogin && (
          <div style={{ textAlign: "center", marginTop: 16, fontSize: "0.875rem" }}>
            <span style={{ color: "#a0aec0" }}>Already cleared? </span>
            <button
              type="button"
              onClick={switchToLogin}
              style={{ background: "none", border: "none", color: "#3182ce", cursor: "pointer", textDecoration: "underline" }}
            >
              Sign in here
            </button>
          </div>
        )}
      </form>
    </div>
  );
}