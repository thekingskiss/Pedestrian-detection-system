import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

const CLASSIFICATION_COLORS = {
  critical: "#e5484d",
  caution: "#f5a524",
  safe: "#3fb950",
};

export default function Zones() {
  const [cameras, setCameras] = useState([]);
  const [zones, setZones] = useState([]);
  const [error, setError] = useState(null);

  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);

  const [previewCameraId, setPreviewCameraId] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [loadingVideo, setLoadingVideo] = useState(false);
  const [liveDetections, setLiveDetections] = useState([]);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  function loadCameras() {
    api.listCameras().then(setCameras).catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadCameras();
    api.listZones().then(setZones).catch((e) => setError(e.message));
  }, []);

  // Clean up the blob URL when it changes or the component unmounts.
  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  // Poll recent detections for the previewed camera while a video is loaded.
  useEffect(() => {
    if (!previewCameraId) {
      setLiveDetections([]);
      return;
    }
    let cancelled = false;
    const poll = () => {
      api
        .listDetections({ camera_id: previewCameraId, limit: 20 })
        .then((rows) => {
          if (!cancelled) setLiveDetections(rows);
        })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 1500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [previewCameraId]);

  // Redraw bounding boxes whenever detections update or the video is resized.
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    function draw() {
      const w = video.clientWidth;
      const h = video.clientHeight;
      if (!w || !h) return;
      canvas.width = w;
      canvas.height = h;

      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, w, h);

      liveDetections.forEach((d) => {
        const b = d.bbox;
        if (!b) return;
        const color = CLASSIFICATION_COLORS[d.classification] || "#94a3b8";
        const x = b.x1 * w;
        const y = b.y1 * h;
        const boxW = (b.x2 - b.x1) * w;
        const boxH = (b.y2 - b.y1) * h;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, boxW, boxH);

        const label = `${d.classification || "?"} ${(d.confidence * 100).toFixed(0)}%`;
        ctx.font = "11px monospace";
        const labelW = ctx.measureText(label).width + 8;
        ctx.fillStyle = color;
        ctx.fillRect(x, Math.max(0, y - 16), labelW, 16);
        ctx.fillStyle = "#0b0f14";
        ctx.fillText(label, x + 4, Math.max(11, y - 4));
      });
    }

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(video);
    return () => observer.disconnect();
  }, [liveDetections]);

  async function loadVideo(cameraId) {
    if (!cameraId) return;

    setLoadingVideo(true);
    setError(null);

    try {
      const blob = await api.getCameraVideoBlob(cameraId);
      const newUrl = URL.createObjectURL(blob);

      setVideoUrl((oldUrl) => {
        if (oldUrl) URL.revokeObjectURL(oldUrl);
        return newUrl;
      });

      setPreviewCameraId(cameraId);
    } catch (err) {
      setError(err.message);
      setVideoUrl("");
    } finally {
      setLoadingVideo(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();

    if (!selectedCameraId || !selectedFile) {
      setUploadMessage({ type: "error", text: "Choose a camera and a video file first." });
      return;
    }

    setUploading(true);
    setUploadMessage(null);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      await api.uploadCameraVideo(selectedCameraId, formData);

      setUploadMessage({ type: "success", text: "Video uploaded successfully. Loading preview..." });
      setSelectedFile(null);
      loadCameras();

      await loadVideo(selectedCameraId);

      setUploadMessage({ type: "success", text: "Video uploaded and ready for detection testing." });
    } catch (err) {
      setUploadMessage({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  }

  function restartVideo() {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play();
    }
  }

  function pauseVideo() {
    if (videoRef.current) videoRef.current.pause();
  }

  function playVideo() {
    if (videoRef.current) videoRef.current.play();
  }

  const previewCamera = cameras.find((camera) => String(camera.id) === String(previewCameraId));

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
        <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 520 }}>
          <label style={{ fontSize: 13 }}>
            Camera
            <select
              value={selectedCameraId}
              onChange={(e) => setSelectedCameraId(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
            >
              <option value="">Select a camera...</option>
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

          {selectedFile && (
            <div style={{ fontSize: 12, color: "var(--slate-400)" }}>Selected: {selectedFile.name}</div>
          )}

          <button type="submit" disabled={uploading} style={{ alignSelf: "flex-start" }}>
            {uploading ? "Uploading..." : "Upload & activate"}
          </button>

          {uploadMessage && (
            <div
              style={{
                color: uploadMessage.type === "error" ? "var(--critical-red, #e5484d)" : "var(--safe-green)",
              }}
            >
              {uploadMessage.text}
            </div>
          )}
        </form>
      </div>

      <h2 style={{ marginBottom: 12, fontSize: 15 }}>Detection Preview</h2>
      <div className="bbox-card" style={{ padding: 20, marginBottom: 28 }}>
        <div className="corner-tl" />
        <div className="corner-br" />

        {!videoUrl && !loadingVideo && (
          <div
            style={{
              minHeight: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              color: "var(--slate-400)",
              border: "1px dashed var(--slate-500)",
            }}
          >
            <div>
              <div style={{ fontSize: 16, marginBottom: 8 }}>No video loaded</div>
              <div style={{ fontSize: 13 }}>Upload a video above to begin detection testing.</div>
            </div>
          </div>
        )}

        {loadingVideo && (
          <div style={{ minHeight: 300, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--slate-400)" }}>
            Loading uploaded video...
          </div>
        )}

        {videoUrl && !loadingVideo && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 12, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{previewCamera?.name || "Uploaded Camera"}</div>
                <div style={{ fontSize: 12, color: "var(--slate-400)", marginTop: 3 }}>
                  {previewCamera?.location_label || "Video test source"}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" onClick={playVideo}>Play</button>
                <button type="button" onClick={pauseVideo}>Pause</button>
                <button type="button" onClick={restartVideo}>Restart</button>
              </div>
            </div>

            <div style={{ position: "relative", width: "100%", background: "#000", overflow: "hidden", borderRadius: 4 }}>
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                playsInline
                preload="metadata"
                style={{ display: "block", width: "100%", maxHeight: "600px", background: "#000" }}
              />

              <canvas
                ref={canvasRef}
                style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
              />

              <div
                style={{
                  position: "absolute",
                  top: 12,
                  left: 12,
                  padding: "6px 10px",
                  background: "rgba(0, 0, 0, 0.65)",
                  color: "#fff",
                  fontSize: 11,
                  borderRadius: 3,
                  pointerEvents: "none",
                }}
              >
                LIVE DETECTION PREVIEW
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, marginTop: 14 }}>
              <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ fontSize: 11, color: "var(--slate-400)" }}>SOURCE</div>
                <div style={{ marginTop: 4, fontSize: 13 }}>Uploaded video</div>
              </div>
              <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ fontSize: 11, color: "var(--slate-400)" }}>CAMERA</div>
                <div style={{ marginTop: 4, fontSize: 13 }}>{previewCamera?.name || "-"}</div>
              </div>
              <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ fontSize: 11, color: "var(--slate-400)" }}>DETECTIONS (recent)</div>
                <div style={{ marginTop: 4, fontSize: 13, color: liveDetections.length ? "var(--safe-green)" : "var(--slate-400)" }}>
                  {liveDetections.length}
                </div>
              </div>
              <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ fontSize: 11, color: "var(--slate-400)" }}>TARGET FPS</div>
                <div style={{ marginTop: 4, fontSize: 13 }}>{previewCamera?.target_fps || "-"}</div>
              </div>
            </div>
          </>
        )}
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
              <th>Preview</th>
            </tr>
          </thead>
          <tbody>
            {cameras.length === 0 && (
              <tr><td colSpan={6} style={{ color: "var(--slate-400)" }}>No cameras registered yet.</td></tr>
            )}
            {cameras.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.source_type}</td>
                <td>{c.location_label || "-"}</td>
                <td>{c.target_fps}</td>
                <td style={{ color: c.is_active ? "var(--safe-green)" : "var(--slate-400)" }}>
                  {c.is_active ? "active" : "inactive"}
                </td>
                <td>
                  {c.source_type === "upload" ? (
                    <button type="button" onClick={() => loadVideo(c.id)}>View video</button>
                  ) : (
                    "-"
                  )}
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
