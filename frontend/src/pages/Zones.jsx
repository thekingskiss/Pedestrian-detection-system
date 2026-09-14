import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function Zones() {
  const [cameras, setCameras] = useState([]);
  const [zones, setZones] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listCameras().then(setCameras).catch((e) => setError(e.message));
    api.listZones().then(setZones).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">FR-01 / FR-06 / FR-11</div>
          <h1 className="page-title">Cameras &amp; Risk Zones</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <h2 style={{ marginBottom: 12, fontSize: 15 }}>Cameras</h2>
      <div className="bbox-card" style={{ padding: 0, marginBottom: 28 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Source</th>
              <th>Location</th>
              <th>Target FPS</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {cameras.length === 0 && (
              <tr><td colSpan={5} style={{ color: "var(--slate-400)" }}>No cameras registered yet.</td></tr>
            )}
            {cameras.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.source_type}</td>
                <td>{c.location_label || "—"}</td>
                <td>{c.target_fps}</td>
                <td style={{ color: c.is_active ? "var(--safe-green)" : "var(--slate-400)" }}>
                  {c.is_active ? "active" : "inactive"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginBottom: 12, fontSize: 15 }}>Risk Zones</h2>
      <div className="bbox-card" style={{ padding: 0 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <table>
          <thead>
            <tr>
              <th>Zone</th>
              <th>Camera</th>
              <th>Safe distance (m)</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {zones.length === 0 && (
              <tr><td colSpan={4} style={{ color: "var(--slate-400)" }}>No zones configured yet.</td></tr>
            )}
            {zones.map((z) => (
              <tr key={z.id}>
                <td>{z.name}</td>
                <td>{cameras.find((c) => c.id === z.camera_id)?.name || z.camera_id}</td>
                <td>{z.safe_distance_meters}</td>
                <td>{z.polygon.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
