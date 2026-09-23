
import React, {
  useEffect,
  useRef,
  useState,
} from "react";
import { api } from "../api/client.js";

const CLASSIFICATION_COLORS = {
  critical: "#e5484d",
  caution: "#f5a524",
  safe: "#3fb950",
};

const DETECTION_SOURCE_FPS = 15;
const DETECTION_WINDOW_SECONDS = 1.25;
const DETECTION_MATCH_TOLERANCE = 0.12;
const DETECTION_REFRESH_MS = 500;
const UPLOAD_CLOCK_BUFFER_SECONDS = 5;

function getMatchingDetections(rows, currentTime) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return [];
  }

  if (!Number.isFinite(currentTime)) {
    return [];
  }

  let nearestTimestamp = null;
  let nearestDifference = Infinity;

  for (const detection of rows) {
    const sourceTime = Number(
      detection?.source_timestamp
    );

    if (!Number.isFinite(sourceTime)) {
      continue;
    }

    const difference = Math.abs(
      sourceTime - currentTime
    );

    if (difference < nearestDifference) {
      nearestDifference = difference;
      nearestTimestamp = sourceTime;
    }
  }

  if (
    nearestTimestamp === null ||
    nearestDifference > DETECTION_MATCH_TOLERANCE
  ) {
    return [];
  }

  /*
   * Select detections belonging to the same processed
   * source frame as the nearest timestamp.
   */
  const sameFrame = rows.filter((detection) => {
    const sourceTime = Number(
      detection?.source_timestamp
    );

    return (
      Number.isFinite(sourceTime) &&
      Math.abs(
        sourceTime - nearestTimestamp
      ) <= 0.06
    );
  });

  /*
   * A video can be processed more than once.
   * Keep only the newest database record for each
   * track/frame combination.
   */
  const byTrackAndFrame = new Map();

  for (const detection of sameFrame) {
    const sourceTime = Number(
      detection.source_timestamp
    );

    const frameBucket = Math.round(
      sourceTime * DETECTION_SOURCE_FPS
    );

    const trackId =
      detection.track_id ?? "unknown";

    const key =
      String(trackId) + "-" + String(frameBucket);

    const existing =
      byTrackAndFrame.get(key);

    if (!existing) {
      byTrackAndFrame.set(
        key,
        detection
      );
      continue;
    }

    const existingCreated =
      new Date(
        existing.timestamp || 0
      ).getTime();

    const currentCreated =
      new Date(
        detection.timestamp || 0
      ).getTime();

    if (
      currentCreated >= existingCreated
    ) {
      byTrackAndFrame.set(
        key,
        detection
      );
    }
  }

  return Array.from(
    byTrackAndFrame.values()
  );
}

function clampNormalized(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return null;
  }

  return Math.max(
    0,
    Math.min(1, number)
  );
}

function normalizeDetection(detection) {
  const sourceTimestamp = Number(
    detection?.source_timestamp
  );

  const bbox = detection?.bbox;

  if (
    !Number.isFinite(sourceTimestamp) ||
    !bbox
  ) {
    return null;
  }

  const x1 = clampNormalized(
    bbox.x1
  );

  const y1 = clampNormalized(
    bbox.y1
  );

  const x2 = clampNormalized(
    bbox.x2
  );

  const y2 = clampNormalized(
    bbox.y2
  );

  if (
    x1 === null ||
    y1 === null ||
    x2 === null ||
    y2 === null
  ) {
    return null;
  }

  if (
    x2 <= x1 ||
    y2 <= y1
  ) {
    return null;
  }

  return {
    ...detection,
    source_timestamp:
      sourceTimestamp,
    bbox: {
      x1,
      y1,
      x2,
      y2,
    },
  };
}

export default function Zones() {
  const [cameras, setCameras] = useState([]);
  const [zones, setZones] = useState([]);
  const [error, setError] = useState(null);

  const [selectedCameraId, setSelectedCameraId] =
    useState("");

  const [selectedFile, setSelectedFile] =
    useState(null);

  const [uploading, setUploading] =
    useState(false);

  const [uploadMessage, setUploadMessage] =
    useState(null);

  const [previewCameraId, setPreviewCameraId] =
    useState("");

  const [detectionStartTime, setDetectionStartTime] =
    useState(null);

  const [videoUrl, setVideoUrl] =
    useState("");

  const [loadingVideo, setLoadingVideo] =
    useState(false);

  const [loadingDetections, setLoadingDetections] =
    useState(false);

  const [liveDetections, setLiveDetections] =
    useState([]);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const videoContainerRef = useRef(null);

  const detectionsRef = useRef([]);

  const requestInFlightRef =
    useRef(false);

  const lastRequestedTimeRef =
    useRef(-1);

  function setPageError(message) {
    setError(
      message || null
    );
  }

  function loadCameras() {
    api
      .listCameras()
      .then(setCameras)
      .catch((err) => {
        setPageError(
          err.message ||
            "Unable to load cameras."
        );
      });
  }

  function loadZones() {
    api
      .listZones()
      .then(setZones)
      .catch((err) => {
        setPageError(
          err.message ||
            "Unable to load risk zones."
        );
      });
  }

  useEffect(() => {
    loadCameras();
    loadZones();
  }, []);

  /*
   * Release blob URLs when they are replaced
   * or when the component is unmounted.
   */
  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(
          videoUrl
        );
      }
    };
  }, [videoUrl]);

  /*
   * Clear old detections whenever the preview
   * camera or upload session changes.
   */
  useEffect(() => {
    detectionsRef.current = [];
    requestInFlightRef.current = false;
    lastRequestedTimeRef.current = -1;

    setLiveDetections([]);
  }, [
    previewCameraId,
    detectionStartTime,
  ]);

  /*
   * Load detections around the current video time.
   */
  useEffect(() => {
    if (!previewCameraId) {
      setLiveDetections([]);
      detectionsRef.current = [];

      return undefined;
    }

    let cancelled = false;

    detectionsRef.current = [];
    requestInFlightRef.current = false;
    lastRequestedTimeRef.current = -1;

    async function loadDetections(
      force = false
    ) {
      const video =
        videoRef.current;

      if (!video) {
        return;
      }

      const currentTime =
        Number(
          video.currentTime
        );

      if (
        !Number.isFinite(
          currentTime
        )
      ) {
        return;
      }

      const lastRequestedTime =
        lastRequestedTimeRef.current;

      if (
        !force &&
        lastRequestedTime >= 0 &&
        Math.abs(
          currentTime -
            lastRequestedTime
        ) < 0.35
      ) {
        return;
      }

      if (
        requestInFlightRef.current
      ) {
        return;
      }

      requestInFlightRef.current =
        true;

      lastRequestedTimeRef.current =
        currentTime;

      const params = {
        camera_id:
          previewCameraId,

        source_start:
          Math.max(
            0,
            currentTime -
              DETECTION_WINDOW_SECONDS
          ),

        source_end:
          currentTime +
          DETECTION_WINDOW_SECONDS,

        limit: 500,
      };

      /*
       * Only use detections created after the
       * current upload session began.
       */
      if (detectionStartTime) {
        params.start =
          detectionStartTime;
      }

      try {
        if (!cancelled) {
          setLoadingDetections(
            true
          );
        }

        const rows =
          await api.listDetections(
            params
          );

        if (cancelled) {
          return;
        }

        const usable = Array.isArray(
          rows
        )
          ? rows
              .map(
                normalizeDetection
              )
              .filter(
                Boolean
              )
          : [];

        detectionsRef.current =
          usable;

        const matching =
          getMatchingDetections(
            usable,
            currentTime
          );

        setLiveDetections(
          matching
        );
      } catch (err) {
        if (!cancelled) {
          detectionsRef.current =
            [];

          setLiveDetections([]);

          setPageError(
            err.message ||
              "Unable to load detections."
          );
        }
      } finally {
        /*
         * Important:
         * Do not let an old cancelled request
         * modify the state of a newer effect.
         */
        if (!cancelled) {
          requestInFlightRef.current =
            false;

          setLoadingDetections(
            false
          );
        }
      }
    }

    function handleTimeUpdate() {
      if (cancelled) {
        return;
      }

      const video =
        videoRef.current;

      if (!video) {
        return;
      }

      const currentTime =
        Number(
          video.currentTime
        );

      if (
        !Number.isFinite(
          currentTime
        )
      ) {
        return;
      }

      const matching =
        getMatchingDetections(
          detectionsRef.current,
          currentTime
        );

      setLiveDetections(
        matching
      );
    }

    function handleSeeked() {
      loadDetections(true);
    }

    function handlePlay() {
      loadDetections(true);
    }

    const video =
      videoRef.current;

    if (video) {
      video.addEventListener(
        "timeupdate",
        handleTimeUpdate
      );

      video.addEventListener(
        "seeked",
        handleSeeked
      );

      video.addEventListener(
        "play",
        handlePlay
      );
    }

    loadDetections(true);

    const refreshId =
      setInterval(() => {
        loadDetections(false);
      }, DETECTION_REFRESH_MS);

    return () => {
      cancelled = true;

      clearInterval(
        refreshId
      );

      if (video) {
        video.removeEventListener(
          "timeupdate",
          handleTimeUpdate
        );

        video.removeEventListener(
          "seeked",
          handleSeeked
        );

        video.removeEventListener(
          "play",
          handlePlay
        );
      }

      detectionsRef.current =
        [];

      requestInFlightRef.current =
        false;

      lastRequestedTimeRef.current =
        -1;
    };
  }, [
    previewCameraId,
    detectionStartTime,
  ]);

  /*
   * Draw detections over the actual displayed video.
   *
   * This supports:
   * - normal full-frame video
   * - browser letterboxing
   * - browser pillarboxing
   */
  useEffect(() => {
    const canvas =
      canvasRef.current;

    const video =
      videoRef.current;

    const container =
      videoContainerRef.current;

    if (
      !canvas ||
      !video ||
      !container
    ) {
      return undefined;
    }

    function getDisplayedVideoRect() {
      const containerRect =
        container.getBoundingClientRect();

      const videoRect =
        video.getBoundingClientRect();

      const elementWidth =
        video.clientWidth;

      const elementHeight =
        video.clientHeight;

      const sourceWidth =
        video.videoWidth;

      const sourceHeight =
        video.videoHeight;

      /*
       * Metadata may not have loaded yet.
       */
      if (
        !elementWidth ||
        !elementHeight ||
        !sourceWidth ||
        !sourceHeight
      ) {
        return {
          left:
            videoRect.left -
            containerRect.left,

          top:
            videoRect.top -
            containerRect.top,

          width:
            videoRect.width,

          height:
            videoRect.height,
        };
      }

      const sourceAspect =
        sourceWidth /
        sourceHeight;

      const elementAspect =
        elementWidth /
        elementHeight;

      let contentWidth =
        elementWidth;

      let contentHeight =
        elementHeight;

      let contentLeft = 0;
      let contentTop = 0;

      /*
       * Match object-fit: contain.
       */
      if (
        Math.abs(
          sourceAspect -
            elementAspect
        ) > 0.001
      ) {
        if (
          elementAspect >
          sourceAspect
        ) {
          /*
           * Pillarboxing:
           * content is narrower than element.
           */
          contentHeight =
            elementHeight;

          contentWidth =
            contentHeight *
            sourceAspect;

          contentLeft =
            (elementWidth -
              contentWidth) /
            2;
        } else {
          /*
           * Letterboxing:
           * content is shorter than element.
           */
          contentWidth =
            elementWidth;

          contentHeight =
            contentWidth /
            sourceAspect;

          contentTop =
            (elementHeight -
              contentHeight) /
            2;
        }
      }

      return {
        left:
          videoRect.left -
          containerRect.left +
          contentLeft,

        top:
          videoRect.top -
          containerRect.top +
          contentTop,

        width:
          contentWidth,

        height:
          contentHeight,
      };
    }

    function draw() {
      const containerRect =
        container.getBoundingClientRect();

      const canvasWidth =
        Math.max(
          1,
          Math.round(
            containerRect.width
          )
        );

      const canvasHeight =
        Math.max(
          1,
          Math.round(
            containerRect.height
          )
        );

      const pixelRatio =
        window.devicePixelRatio ||
        1;

      canvas.width =
        Math.round(
          canvasWidth *
            pixelRatio
        );

      canvas.height =
        Math.round(
          canvasHeight *
            pixelRatio
        );

      canvas.style.width =
        `${canvasWidth}px`;

      canvas.style.height =
        `${canvasHeight}px`;

      const ctx =
        canvas.getContext(
          "2d"
        );

      if (!ctx) {
        return;
      }

      ctx.setTransform(
        pixelRatio,
        0,
        0,
        pixelRatio,
        0,
        0
      );

      ctx.clearRect(
        0,
        0,
        canvasWidth,
        canvasHeight
      );

      const content =
        getDisplayedVideoRect();

      for (
        const detection of
          liveDetections
      ) {
        const b =
          detection?.bbox;

        if (!b) {
          continue;
        }

        const x1 =
          clampNormalized(
            b.x1
          );

        const y1 =
          clampNormalized(
            b.y1
          );

        const x2 =
          clampNormalized(
            b.x2
          );

        const y2 =
          clampNormalized(
            b.y2
          );

        if (
          x1 === null ||
          y1 === null ||
          x2 === null ||
          y2 === null ||
          x2 <= x1 ||
          y2 <= y1
        ) {
          continue;
        }

        const x =
          content.left +
          x1 * content.width;

        const y =
          content.top +
          y1 * content.height;

        const boxWidth =
          (x2 - x1) *
          content.width;

        const boxHeight =
          (y2 - y1) *
          content.height;

        const classification =
          String(
            detection.classification ||
              "safe"
          ).toLowerCase();

        const color =
          CLASSIFICATION_COLORS[
            classification
          ] || "#94a3b8";

        /*
         * Bounding box.
         */
        ctx.strokeStyle =
          color;

        ctx.lineWidth = 3;

        ctx.strokeRect(
          x,
          y,
          boxWidth,
          boxHeight
        );

        /*
         * Confidence label.
         */
        const confidence =
          Number(
            detection.confidence
          );

        const confidenceText =
          Number.isFinite(
            confidence
          )
            ? `${(
                confidence * 100
              ).toFixed(0)}%`
            : "--";

        const label =
          `${classification} ${confidenceText}`;

        ctx.font =
          "bold 11px monospace";

        const labelWidth =
          ctx.measureText(
            label
          ).width + 10;

        const labelHeight =
          18;

        const labelX =
          Math.max(
            content.left,
            Math.min(
              x,
              content.left +
                content.width -
                labelWidth
            )
          );

        const labelY =
          y -
            labelHeight >=
          content.top
            ? y - labelHeight
            : y;

        ctx.fillStyle =
          color;

        ctx.fillRect(
          labelX,
          labelY,
          labelWidth,
          labelHeight
        );

        ctx.fillStyle =
          "#0b0f14";

        ctx.fillText(
          label,
          labelX + 5,
          labelY + 13
        );
      }
    }

    draw();

    const observer =
      new ResizeObserver(draw);

    observer.observe(
      container
    );

    video.addEventListener(
      "loadedmetadata",
      draw
    );

    video.addEventListener(
      "loadeddata",
      draw
    );

    video.addEventListener(
      "durationchange",
      draw
    );

    video.addEventListener(
      "canplay",
      draw
    );

    window.addEventListener(
      "resize",
      draw
    );

    return () => {
      observer.disconnect();

      video.removeEventListener(
        "loadedmetadata",
        draw
      );

      video.removeEventListener(
        "loadeddata",
        draw
      );

      video.removeEventListener(
        "durationchange",
        draw
      );

      video.removeEventListener(
        "canplay",
        draw
      );

      window.removeEventListener(
        "resize",
        draw
      );
    };
  }, [liveDetections]);

  async function loadVideo(
    cameraId,
    sessionStartTime = null
  ) {
    if (!cameraId) {
      return;
    }

    setLoadingVideo(true);
    setPageError(null);
    setUploadMessage(null);
    setLiveDetections([]);

    detectionsRef.current =
      [];

    requestInFlightRef.current =
      false;

    lastRequestedTimeRef.current =
      -1;

    try {
      const blob =
        await api.getCameraVideoBlob(
          cameraId
        );

      if (!(blob instanceof Blob)) {
        throw new Error(
          "The camera video could not be loaded."
        );
      }

      const newUrl =
        URL.createObjectURL(
          blob
        );

      setVideoUrl(
        newUrl
      );

      setDetectionStartTime(
        sessionStartTime
      );

      setPreviewCameraId(
        cameraId
      );
    } catch (err) {
      setVideoUrl("");
      setPreviewCameraId("");
      setDetectionStartTime(
        null
      );
      setLiveDetections([]);

      detectionsRef.current =
        [];

      setPageError(
        err.message ||
          "Unable to load camera video."
      );
    } finally {
      setLoadingVideo(false);
    }
  }

  async function handleUpload(
    event
  ) {
    event.preventDefault();

    setPageError(null);
    setUploadMessage(null);

    if (!selectedCameraId) {
      setUploadMessage({
        type: "error",
        text:
          "Choose a camera first.",
      });

      return;
    }

    if (!selectedFile) {
      setUploadMessage({
        type: "error",
        text:
          "Choose a video file first.",
      });

      return;
    }

    if (
      !selectedFile.type.startsWith(
        "video/"
      )
    ) {
      setUploadMessage({
        type: "error",
        text:
          "Please choose a valid video file.",
      });

      return;
    }

    setUploading(true);

    try {
      /*
       * Start slightly before the upload request.
       * This helps include detections if there is
       * a tiny browser/container clock difference.
       */
      const sessionStartTime =
        new Date(
          Date.now() -
            UPLOAD_CLOCK_BUFFER_SECONDS *
              1000
        ).toISOString();

      const formData =
        new FormData();

      formData.append(
        "file",
        selectedFile
      );

      await api.uploadCameraVideo(
        selectedCameraId,
        formData
      );

      setUploadMessage({
        type: "success",
        text:
          "Video uploaded successfully. Loading preview...",
      });

      setSelectedFile(
        null
      );

      loadCameras();

      await loadVideo(
        selectedCameraId,
        sessionStartTime
      );

      setUploadMessage({
        type: "success",
        text:
          "Video uploaded and ready for detection testing.",
      });
    } catch (err) {
      setUploadMessage({
        type: "error",
        text:
          err.message ||
          "Video upload failed.",
      });
    } finally {
      setUploading(false);
    }
  }

  function restartVideo() {
    const video =
      videoRef.current;

    if (!video) {
      return;
    }

    video.currentTime = 0;

    /*
     * Refresh detections immediately for frame 0.
     */
    const currentTime =
      Number(
        video.currentTime
      );

    if (
      Number.isFinite(
        currentTime
      )
    ) {
      setLiveDetections(
        getMatchingDetections(
          detectionsRef.current,
          currentTime
        )
      );
    }

    const playPromise =
      video.play();

    if (
      playPromise &&
      typeof playPromise.catch ===
        "function"
    ) {
      playPromise.catch(() => {
        setPageError(
          "Press the video play button to start playback."
        );
      });
    }
  }

  function pauseVideo() {
    const video =
      videoRef.current;

    if (video) {
      video.pause();
    }
  }

  function playVideo() {
    const video =
      videoRef.current;

    if (!video) {
      return;
    }

    const playPromise =
      video.play();

    if (
      playPromise &&
      typeof playPromise.catch ===
        "function"
    ) {
      playPromise.catch(() => {
        setPageError(
          "The browser blocked playback. Press the video play button."
        );
      });
    }
  }

  function clearPreview() {
    if (videoRef.current) {
      videoRef.current.pause();

      videoRef.current.removeAttribute(
        "src"
      );

      videoRef.current.load();
    }

    setVideoUrl("");
    setPreviewCameraId("");
    setDetectionStartTime(
      null
    );
    setLiveDetections([]);

    detectionsRef.current =
      [];

    requestInFlightRef.current =
      false;

    lastRequestedTimeRef.current =
      -1;
  }

  const previewCamera =
    cameras.find(
      (camera) =>
        String(camera.id) ===
        String(previewCameraId)
    );

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">
            FR-01 / FR-06 / FR-11
          </div>

          <h1 className="page-title">
            Cameras &amp; Risk Zones
          </h1>
        </div>
      </div>

      {error && (
        <div className="error-text">
          {error}
        </div>
      )}

      <h2
        style={{
          marginBottom: 12,
          fontSize: 15,
        }}
      >
        Upload video for testing
      </h2>

      <div
        className="bbox-card"
        style={{
          padding: 20,
          marginBottom: 28,
        }}
      >
        <div className="corner-tl" />
        <div className="corner-br" />

        <form
          onSubmit={handleUpload}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            maxWidth: 520,
          }}
        >
          <label
            style={{
              fontSize: 13,
            }}
          >
            Camera

            <select
              value={
                selectedCameraId
              }
              onChange={(event) =>
                setSelectedCameraId(
                  event.target.value
                )
              }
              disabled={uploading}
              style={{
                display: "block",
                width: "100%",
                marginTop: 4,
                padding: 8,
              }}
            >
              <option value="">
                Select a camera...
              </option>

              {cameras.map(
                (camera) => (
                  <option
                    key={camera.id}
                    value={camera.id}
                  >
                    {camera.name}
                  </option>
                )
              )}
            </select>
          </label>

          <label
            style={{
              fontSize: 13,
            }}
          >
            Video file

            <input
              type="file"
              accept="video/*"
              disabled={uploading}
              onChange={(event) =>
                setSelectedFile(
                  event.target.files?.[0] ||
                    null
                )
              }
              style={{
                display: "block",
                width: "100%",
                marginTop: 4,
              }}
            />
          </label>

          {selectedFile && (
            <div
              style={{
                fontSize: 12,
                color:
                  "var(--slate-400)",
              }}
            >
              Selected:{" "}
              {selectedFile.name}
            </div>
          )}

          <button
            type="submit"
            disabled={uploading}
            style={{
              alignSelf:
                "flex-start",
            }}
          >
            {uploading
              ? "Uploading..."
              : "Upload & activate"}
          </button>

          {uploadMessage && (
            <div
              style={{
                color:
                  uploadMessage.type ===
                  "error"
                    ? "var(--critical-red, #e5484d)"
                    : "var(--safe-green)",
              }}
            >
              {uploadMessage.text}
            </div>
          )}
        </form>
      </div>

      <h2
        style={{
          marginBottom: 12,
          fontSize: 15,
        }}
      >
        Detection Preview
      </h2>

      <div
        className="bbox-card"
        style={{
          padding: 20,
          marginBottom: 28,
        }}
      >
        <div className="corner-tl" />
        <div className="corner-br" />

        {!videoUrl &&
          !loadingVideo && (
            <div
              style={{
                minHeight: 300,
                display: "flex",
                alignItems:
                  "center",
                justifyContent:
                  "center",
                textAlign: "center",
                color:
                  "var(--slate-400)",
                border:
                  "1px dashed var(--slate-500)",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 16,
                    marginBottom: 8,
                  }}
                >
                  No video loaded
                </div>

                <div
                  style={{
                    fontSize: 13,
                  }}
                >
                  Upload a video
                  above to begin
                  detection testing.
                </div>
              </div>
            </div>
          )}

        {loadingVideo && (
          <div
            style={{
              minHeight: 300,
              display: "flex",
              alignItems:
                "center",
              justifyContent:
                "center",
              color:
                "var(--slate-400)",
            }}
          >
            Loading uploaded video...
          </div>
        )}

        {videoUrl &&
          !loadingVideo && (
            <>
              <div
                style={{
                  display: "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "center",
                  marginBottom: 12,
                  gap: 12,
                  flexWrap:
                    "wrap",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                    }}
                  >
                    {previewCamera?.name ||
                      "Uploaded Camera"}
                  </div>

                  <div
                    style={{
                      fontSize: 12,
                      color:
                        "var(--slate-400)",
                      marginTop: 3,
                    }}
                  >
                    {previewCamera?.location_label ||
                      "Video test source"}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexWrap:
                      "wrap",
                  }}
                >
                  <button
                    type="button"
                    onClick={
                      playVideo
                    }
                  >
                    Play
                  </button>

                  <button
                    type="button"
                    onClick={
                      pauseVideo
                    }
                  >
                    Pause
                  </button>

                  <button
                    type="button"
                    onClick={
                      restartVideo
                    }
                  >
                    Restart
                  </button>

                  <button
                    type="button"
                    onClick={
                      clearPreview
                    }
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div
                ref={
                  videoContainerRef
                }
                style={{
                  position:
                    "relative",
                  width: "100%",
                  background:
                    "#000",
                  overflow:
                    "hidden",
                  borderRadius: 4,
                  lineHeight: 0,
                }}
              >
                <video
                  ref={videoRef}
                  src={videoUrl}
                  controls
                  playsInline
                  preload="metadata"
                  onLoadedMetadata={() => {
                    setLiveDetections(
                      []
                    );
                  }}
                  onError={() => {
                    setPageError(
                      "The video could not be played by the browser."
                    );
                  }}
                  style={{
                    display:
                      "block",
                    width:
                      "100%",
                    height:
                      "auto",
                    background:
                      "#000",
                    objectFit:
                      "contain",
                  }}
                />

                <canvas
                  ref={canvasRef}
                  style={{
                    position:
                      "absolute",
                    top: 0,
                    left: 0,
                    width:
                      "100%",
                    height:
                      "100%",
                    pointerEvents:
                      "none",
                  }}
                />

                <div
                  style={{
                    position:
                      "absolute",
                    top: 12,
                    left: 12,
                    padding:
                      "6px 10px",
                    background:
                      "rgba(0, 0, 0, 0.65)",
                    color:
                      "#fff",
                    fontSize: 11,
                    borderRadius:
                      3,
                    pointerEvents:
                      "none",
                  }}
                >
                  LIVE DETECTION PREVIEW
                </div>

                {loadingDetections && (
                  <div
                    style={{
                      position:
                        "absolute",
                      top: 12,
                      right: 12,
                      padding:
                        "6px 10px",
                      background:
                        "rgba(0, 0, 0, 0.65)",
                      color:
                        "#fff",
                      fontSize: 11,
                      borderRadius:
                        3,
                      pointerEvents:
                        "none",
                    }}
                  >
                    Syncing detections...
                  </div>
                )}
              </div>

              <div
                style={{
                  display:
                    "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(140px, 1fr))",
                  gap: 10,
                  marginTop: 14,
                }}
              >
                <div
                  style={{
                    padding: 12,
                    border:
                      "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color:
                        "var(--slate-400)",
                    }}
                  >
                    SOURCE
                  </div>

                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    Uploaded video
                  </div>
                </div>

                <div
                  style={{
                    padding: 12,
                    border:
                      "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color:
                        "var(--slate-400)",
                    }}
                  >
                    CAMERA
                  </div>

                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    {previewCamera?.name ||
                      "-"}
                  </div>
                </div>

                <div
                  style={{
                    padding: 12,
                    border:
                      "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color:
                        "var(--slate-400)",
                    }}
                  >
                    DETECTIONS
                  </div>

                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                      color:
                        liveDetections.length
                          ? "var(--safe-green)"
                          : "var(--slate-400)",
                    }}
                  >
                    {liveDetections.length}
                  </div>
                </div>

                <div
                  style={{
                    padding: 12,
                    border:
                      "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      color:
                        "var(--slate-400)",
                    }}
                  >
                    TARGET FPS
                  </div>

                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 13,
                    }}
                  >
                    {previewCamera?.target_fps ||
                      "-"}
                  </div>
                </div>
              </div>
            </>
          )}
      </div>

      <h2
        style={{
          marginBottom: 12,
          fontSize: 15,
        }}
      >
        Cameras
      </h2>

      <div
        className="bbox-card"
        style={{
          padding: 0,
          marginBottom: 28,
        }}
      >
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
              <tr>
                <td
                  colSpan={6}
                  style={{
                    color:
                      "var(--slate-400)",
                  }}
                >
                  No cameras registered
                  yet.
                </td>
              </tr>
            )}

            {cameras.map(
              (camera) => (
                <tr
                  key={camera.id}
                >
                  <td>
                    {camera.name}
                  </td>

                  <td>
                    {
                      camera.source_type
                    }
                  </td>

                  <td>
                    {camera.location_label ||
                      "-"}
                  </td>

                  <td>
                    {
                      camera.target_fps
                    }
                  </td>

                  <td
                    style={{
                      color:
                        camera.is_active
                          ? "var(--safe-green)"
                          : "var(--slate-400)",
                    }}
                  >
                    {camera.is_active
                      ? "active"
                      : "inactive"}
                  </td>

                  <td>
                    {camera.source_type ===
                    "upload" ? (
                      <button
                        type="button"
                        onClick={() =>
                          loadVideo(
                            camera.id
                          )
                        }
                      >
                        View video
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>

      <h2
        style={{
          marginBottom: 12,
          fontSize: 15,
        }}
      >
        Risk Zones
      </h2>

      <div
        className="bbox-card"
        style={{
          padding: 0,
        }}
      >
        <div className="corner-tl" />
        <div className="corner-br" />

        <table>
          <thead>
            <tr>
              <th>Zone</th>
              <th>Camera</th>
              <th>
                Safe distance (m)
              </th>
              <th>Points</th>
            </tr>
          </thead>

          <tbody>
            {zones.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  style={{
                    color:
                      "var(--slate-400)",
                  }}
                >
                  No zones configured
                  yet.
                </td>
              </tr>
            )}

            {zones.map(
              (zone) => (
                <tr
                  key={zone.id}
                >
                  <td>
                    {zone.name}
                  </td>

                  <td>
                    {cameras.find(
                      (camera) =>
                        String(
                          camera.id
                        ) ===
                        String(
                          zone.camera_id
                        )
                    )?.name ||
                      zone.camera_id}
                  </td>

                  <td>
                    {
                      zone.safe_distance_meters
                    }
                  </td>

                  <td>
                    {zone.polygon?.length ||
                      0}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
