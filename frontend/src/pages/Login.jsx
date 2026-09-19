import React, { useState } from "react";
import { api, setToken } from "../api/client.js";

export default function Login({ onLoggedIn }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (isRegistering && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      if (isRegistering) {
        await api.register(email, password);
        // Automatically log in after successful registration
        const { access_token } = await api.login(email, password);
        setToken(access_token);
        onLoggedIn();
      } else {
        const { access_token } = await api.login(email, password);
        setToken(access_token);
        onLoggedIn();
      }
    } catch (err) {
      setError(err.message || "Operation failed. Please try again.");
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
        <h1 style={{ marginBottom: 24 }}>
          {isRegistering ? "Officer Registration" : "Officer sign-in"}
        </h1>

        <div className="field">
          <label htmlFor="email">Email</label>
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

        {isRegistering && (
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
        )}

        {error && (
          <div className="error-text" style={{ color: "#ff4d4d", marginBottom: 12, fontSize: "0.875rem" }}>
            {error}
          </div>
        )}

        <button className="btn" type="submit" disabled={loading} style={{ width: "100%", marginTop: 8 }}>
          {loading ? "Processing…" : isRegistering ? "Create Account" : "Sign in"}
        </button>

        <div style={{ textAlign: "center", marginTop: 16, fontSize: "0.875rem" }}>
          <span style={{ color: "#a0aec0" }}>
            {isRegistering ? "Already cleared? " : "Need an account? "}
          </span>
          <button
            type="button"
            onClick={() => {
              setIsRegistering(!isRegistering);
              setError(null);
            }}
            style={{
              background: "none",
              border: "none",
              color: "#f6ad55",
              cursor: "pointer",
              textDecoration: "underline",
            }}
          >
            {isRegistering ? "Sign in here" : "Register here"}
          </button>
        </div>
      </form>
    </div>
  );
}