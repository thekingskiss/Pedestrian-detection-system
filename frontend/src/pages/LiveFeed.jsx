import React, { useEffect, useState } from "react";
import AlertBadge from "../components/AlertBadge.jsx";
import { api } from "../api/client.js";

/**
 * FR-03..FR-07 read path: shows the most recent DetectionEvents. A real
 * deployment would also render the source video with bounding boxes drawn
 * live (via a canvas overlay reading the same WS stream used for alerts) —
 * left out here since there's no live camera in this environment; this page
 * demonstrates the data contract instead.
 */
export default function LiveFeed() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const data = await api.listDetections({ limit: 30 });
        if (!cancelled) setEvents(data);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }
    poll();
    const interval = setInterval(poll, 4000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">Auto-refreshing every 4s</div>
          <h1 className="page-title">Live Detection Feed</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="bbox-card" style={{ padding: 0 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Track</th>
              <th>Confidence</th>
              <th>Distance (m)</th>
              <th>Closing speed (m/s)</th>
              <th>Classification</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--slate-400)" }}>
                  No events yet — the pipeline worker populates this once a camera is active.
                </td>
              </tr>
            )}
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.timestamp).toLocaleTimeString()}</td>
                <td>#{e.track_id}</td>
                <td>{e.confidence.toFixed(2)}</td>
                <td>{e.distance_estimate_m?.toFixed(1) ?? "—"}</td>
                <td>{e.closing_speed_mps?.toFixed(1) ?? "—"}</td>
                <td><AlertBadge severity={e.classification} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
