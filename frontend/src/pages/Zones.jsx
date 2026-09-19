import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function Zones() {
  const [cameras, setCameras] = useState([]);
  const [zones, setZones] = useState([]);
  const [error, setError] = useState(null);

  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);

  function loadCameras() {
    api.listCameras().then(setCameras).catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadCameras();
    api.listZones().then(setZones).catch((e) => setError(e.message));
  }, []);

  async function handleUpload(e) {
    e.preventDefault();
    if (!selectedCameraId || !selectedFile) {
      setUploadMessage({ type: "error", text: "Choose a camera and a video file first." });
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      await api.uploadCameraVideo(selectedCameraId, formData);
      setUploadMessage({
        type: "success",
        text: "Uploaded — the detection worker will pick this up within ~10 seconds.",
      });
      setSelectedFile(null);
      loadCameras(); // refresh so the table shows the new source
    } catch (err) {
      setUploadMessage({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">FR-01 / FR-06 / FR-11</div>
          <h1 className="page-title">Cameras &amp; Risk Zones</h1>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <h2 style={{ marginBottom: 12, fontSize: 15 }}>Upload video for testing</h2>
      <div className="bbox-card" style={{ padding: 20, marginBottom: 28 }}>
        <div className="corner-tl" />
        <div className="corner-br" />
        <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 480 }}>
          <label style={{ fontSize: 13 }}>
            Camera
            <select
              value={selectedCameraId}
              onChange={(e) => setSelectedCameraId(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
            >
              <option value="">Select a camera…</option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          <label style={{ fontSize: 13 }}>
            Video file
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              style={{ display: "block", width: "100%", marginTop: 4 }}
            />
          </label>

          <button type="submit" disabled={uploading} style={{ alignSelf: "flex-start" }}>
            {uploading ? "Uploading…" : "Upload & activate"}
          </button>

          {uploadMessage && (
            <div style={{ color: uploadMessage.type === "error" ? "var(--critical-red, #e5484d)" : "var(--safe-green)" }}>
              {uploadMessage.text}
            </div>
          )}
        </form>
      </div>

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