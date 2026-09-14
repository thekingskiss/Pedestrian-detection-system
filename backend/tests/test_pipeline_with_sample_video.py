"""
End-to-end test of the detection pipeline against a real (synthetic) video
file, run through the actual production code path: VideoCaptureService ->
FramePreprocessor -> [detector] -> non_max_suppression -> GreedyIouTracker
-> RiskClassifier -> DetectionEvent/Alert persistence (CameraPipeline.run(),
pipeline_orchestrator.py).

The only stand-in is the detector itself: no GPU/ultralytics/pretrained
weights are available in this environment (see ml/yolo_wrapper.py's module
docstring), so `FakeBlobDetector` below finds a solid-red rectangle rendered
into the sample video via simple color thresholding, in place of a real YOLO
forward pass. Everything downstream of "here is a list of Detections for
this frame" is the real, unmodified pipeline code.

The synthetic clip encodes one pedestrian approaching a marked crossing:
starting outside the risk zone, entering it while still beyond the safe
distance, then closing at low speed (CAUTION), then -- after a one-frame
detector dropout standing in for a brief real-world occlusion -- closing at
high speed (CRITICAL). The exact per-frame geometry (and the frame-to-frame
IoU it produces) was verified numerically before being encoded into pixels;
see the design notes in this file's git history / PR description.

Requires a reachable Postgres matching backend/.env (the same one the app
uses) since it exercises real DetectionEvent/Alert persistence, not mocks.
"""
import asyncio
import uuid

import cv2
import numpy as np
import pytest

import app.db.base  # noqa: F401 — registers every model on Base.metadata before any flush
from app.db.session import SessionLocal
from app.ml.yolo_wrapper import Detection
from app.models.alert import Alert
from app.models.camera import CameraFeed
from app.models.detection_event import DetectionEvent
from app.models.zone import RiskZone
from app.services.pipeline_orchestrator import CameraPipeline

FPS = 5
FRAME_W, FRAME_H = 640, 480
ZONE_POLYGON = [[0.3, 0.6], [0.7, 0.6], [0.75, 0.95], [0.25, 0.95]]
BOX_WIDTH = 0.16

# (bottom_y, height) in normalised frame coordinates, or None for a frame
# where the pedestrian is undetected (simulated occlusion/dropout).
# Verified progression: outside_risk_zone x7 -> beyond_safe_distance x3 ->
# in_zone_slow_approach (CAUTION) x1 -> [occluded] -> closing_speed_exceeded
# (CRITICAL) x2.
BLOB_SEQUENCE = [
    (0.18, 0.14), (0.24, 0.15), (0.30, 0.16), (0.36, 0.17), (0.42, 0.18),
    (0.48, 0.19), (0.54, 0.20),
    (0.62, 0.22), (0.66, 0.28), (0.70, 0.34), (0.73, 0.36),
    None,
    (0.80, 0.45), (0.85, 0.55),
]


class FakeBlobDetector:
    """
    Test-only stand-in for YoloPedestrianDetector.predict(): thresholds the
    preprocessed RGB frame for the pure-red rectangle rendered by
    _write_sample_video() and returns its bounding box, so the rest of the
    pipeline is exercised against real decoded/preprocessed video frames
    instead of hand-built Detection objects. Ignores confidence_threshold
    (this test isn't exercising FR-04's confidence-filtering behaviour).
    """

    weights_path = "test-fake-blob-detector"

    def load(self) -> None:
        pass

    def predict(self, image: np.ndarray, confidence_threshold: float) -> list[Detection]:
        red_mask = (image[:, :, 0] > 0.5) & (image[:, :, 1] < 0.3) & (image[:, :, 2] < 0.3)
        mask_u8 = (red_mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = image.shape[:2]
        detections = []
        for contour in contours:
            if cv2.contourArea(contour) < 20:
                continue
            x, y, box_w, box_h = cv2.boundingRect(contour)
            detections.append(
                Detection(x1=x / w, y1=y / h, x2=(x + box_w) / w, y2=(y + box_h) / h, confidence=0.9)
            )
        return detections


def _write_sample_video(path: str) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, FPS, (FRAME_W, FRAME_H))
    try:
        for entry in BLOB_SEQUENCE:
            frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
            if entry is not None:
                bottom, height = entry
                x1 = int((0.5 - BOX_WIDTH / 2) * FRAME_W)
                x2 = int((0.5 + BOX_WIDTH / 2) * FRAME_W)
                y1 = int((bottom - height) * FRAME_H)
                y2 = int(bottom * FRAME_H)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), -1)  # BGR pure red
            writer.write(frame)
    finally:
        writer.release()


@pytest.fixture
def sample_video(tmp_path):
    video_path = tmp_path / "sample_pedestrian_approach.mp4"
    _write_sample_video(str(video_path))
    return str(video_path)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_pipeline_against_sample_video(sample_video, db):
    camera = CameraFeed(
        id=uuid.uuid4(),
        name="TEST — synthetic pedestrian approach",
        source_type="file",
        source_uri=sample_video,
        target_fps=FPS,
    )
    zone = RiskZone(id=uuid.uuid4(), camera_id=camera.id, name="TEST zone", polygon=ZONE_POLYGON)
    db.add_all([camera, zone])
    db.commit()

    try:
        pipeline = CameraPipeline(camera, [zone], db)
        pipeline.detector = FakeBlobDetector()  # swap in the test stand-in
        pipeline._metrics_flush_every = 5  # flush latency/FPS well within this short clip

        asyncio.run(pipeline.run())

        events = (
            db.query(DetectionEvent)
            .filter(DetectionEvent.camera_id == camera.id)
            .order_by(DetectionEvent.timestamp)
            .all()
        )
        non_occluded_frames = sum(1 for entry in BLOB_SEQUENCE if entry is not None)
        assert len(events) == non_occluded_frames, (
            "one DetectionEvent per non-occluded frame; the occluded frame must not "
            "persist a stale duplicate"
        )

        # The pedestrian must be tracked as a single continuous identity —
        # including across the occlusion gap — not fragmented into several
        # track_ids by the position/size jump.
        track_ids = {e.track_id for e in events}
        assert track_ids == {events[0].track_id}, f"expected one continuous track, got {track_ids}"

        classifications = [e.classification for e in events]
        assert classifications.count("safe") == 10  # 7 outside-zone + 3 beyond-safe-distance
        assert classifications.count("caution") == 1
        assert classifications.count("critical") == 2

        rules_fired = [e.reasoning["rule_fired"] for e in events]
        assert rules_fired[:7] == ["outside_risk_zone"] * 7
        assert rules_fired[7:10] == ["beyond_safe_distance"] * 3
        assert rules_fired[10] == "in_zone_slow_approach"
        assert rules_fired[11:] == ["closing_speed_exceeded"] * 2

        # Every event carries the pipeline-level context too, not just the
        # classifier's own decision.
        for event in events:
            assert event.reasoning["lighting_condition"] in ("normal", "low_light")
            assert "confidence_threshold_used" in event.reasoning
            assert event.reasoning["occluded"] is False  # occluded frames aren't persisted at all

        # Alerts fire for every caution/critical event, each carrying a copy
        # of the triggering event's reasoning for officer-facing audit.
        alerts = db.query(Alert).join(DetectionEvent).filter(DetectionEvent.camera_id == camera.id).all()
        assert len(alerts) == 3
        assert sorted(a.severity for a in alerts) == ["caution", "critical", "critical"]
        assert all(a.reasoning is not None for a in alerts)

        # Live pipeline-performance metrics were measured against real
        # decoded frames and flushed back onto the camera row.
        db.refresh(camera)
        assert camera.avg_processing_latency_ms is not None
        assert camera.avg_processing_latency_ms > 0
        assert camera.observed_fps is not None
    finally:
        # Cascades to the zone, its detection_events, and their alerts.
        db.query(CameraFeed).filter(CameraFeed.id == camera.id).delete()
        db.commit()
