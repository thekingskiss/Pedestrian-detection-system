import React, { useEffect, useRef, useState } from "react";
import AlertBadge from "../components/AlertBadge.jsx";
import { api, WS_BASE } from "../api/client.js";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});
  const wsRef = useRef(null);

  useEffect(() => {
    api.listAlerts({ limit: 100 }).then(setAlerts).catch((e) => setError(e.message));

    // FR-08: near-real-time push over the websocket alert channel
    // (see backend/app/api/v1/endpoints/ws.py). Falls back silently to the
    // 100-row snapshot above if the socket can't connect in this environment.
    const token = localStorage.getItem("pds_token");
    if (token) {
      const ws = new WebSocket(`${WS_BASE}/alerts?token=${token}`);
      ws.onmessage = (msg) => {
        try {
          const alert = JSON.parse(msg.data);
          setAlerts((prev) => [alert, ...prev].slice(0, 100));
        } catch {
          /* ignore malformed frame */
        }
      };
      wsRef.current = ws;
    }
    return () => wsRef.current?.close();
  }, []);

  async function handleAcknowledge(id) {
    await api.acknowledgeAlert(id);
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)));
  }

  function toggleReasoning(id) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">Live + last 100</div>
          <h1 className="page-title">Alerts</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div style={{ display: "grid", gap: 10 }}>
        {alerts.length === 0 && (
          <div className="bbox-card" style={{ color: "var(--slate-400)" }}>
            <div className="corner-tl" />
            <div className="corner-br" />
            No alerts yet.
          </div>
        )}
        {alerts.map((a) => (
          <div key={a.id} className={`bbox-card ${a.severity}`}>
            <div className="corner-tl" />
            <div className="corner-br" />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <AlertBadge severity={a.severity} />
                <div style={{ marginTop: 8 }}>{a.message}</div>
                <div className="mono" style={{ fontSize: 11, color: "var(--slate-400)", marginTop: 6 }}>
                  {new Date(a.created_at).toLocaleString()}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {a.reasoning && (
                  <button className="btn secondary" onClick={() => toggleReasoning(a.id)}>
                    {expanded[a.id] ? "Hide reasoning" : "Why?"}
                  </button>
                )}
                {!a.acknowledged ? (
                  <button className="btn secondary" onClick={() => handleAcknowledge(a.id)}>
                    Acknowledge
                  </button>
                ) : (
                  <span className="mono" style={{ fontSize: 11, color: "var(--slate-400)" }}>
                    acknowledged
                  </span>
                )}
              </div>
            </div>
            {a.reasoning && expanded[a.id] && (
              <div className="mono" style={{ fontSize: 11, color: "var(--slate-400)", marginTop: 10, borderTop: "1px solid var(--slate-700, #333)", paddingTop: 8 }}>
                {Object.entries(a.reasoning).map(([key, val]) => (
                  <div key={key} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <span>{key}</span>
                    <span>{String(val)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
