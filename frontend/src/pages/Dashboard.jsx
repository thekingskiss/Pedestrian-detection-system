import React, { useEffect, useState } from "react";
import StatCard from "../components/StatCard.jsx";
import { api } from "../api/client.js";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.dashboardSummary(24).then(setSummary).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">Last 24 hours</div>
          <h1 className="page-title">Overview</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      {summary && (
        <>
          <div className="stat-grid">
            <StatCard label="Total Detections" value={summary.total_detections} />
            <StatCard label="Critical Alerts" value={summary.total_critical_alerts} tone="critical" />
            <StatCard label="Caution Alerts" value={summary.total_caution_alerts} tone="caution" />
            <StatCard label="Active Cameras" value={summary.active_cameras} />
            <StatCard
              label="Avg. Processing Latency"
              value={summary.avg_processing_latency_ms != null ? `${summary.avg_processing_latency_ms.toFixed(0)} ms` : "—"}
            />
            <StatCard
              label="Avg. Observed FPS"
              value={summary.avg_observed_fps != null ? summary.avg_observed_fps.toFixed(1) : "—"}
            />
          </div>

          <h2 style={{ marginBottom: 12, fontSize: 15 }}>Hotspots</h2>
          <div className="bbox-card" style={{ padding: 0 }}>
            <div className="corner-tl" />
            <div className="corner-br" />
            <table>
              <thead>
                <tr>
                  <th>Camera</th>
                  <th>Zone</th>
                  <th>Detections</th>
                  <th>Critical</th>
                </tr>
              </thead>
              <tbody>
                {summary.hotspots.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ color: "var(--slate-400)" }}>
                      No detections logged in this window yet.
                    </td>
                  </tr>
                )}
                {summary.hotspots.map((h, i) => (
                  <tr key={i}>
                    <td>{h.camera_name}</td>
                    <td>{h.zone_name || "—"}</td>
                    <td>{h.detection_count}</td>
                    <td style={{ color: h.critical_count > 0 ? "var(--signal-red)" : undefined }}>
                      {h.critical_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
