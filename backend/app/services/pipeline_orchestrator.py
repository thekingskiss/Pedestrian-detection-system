"""
Wires the full FR-01..FR-09 pipeline together for a single camera:

    VideoCaptureService -> FramePreprocessor -> YoloPedestrianDetector
        -> GreedyIouTracker -> RiskClassifier -> DetectionEvent (+ AlertService)

This intentionally runs as a *separate worker process* per active camera,
not inline inside the FastAPI request/response cycle: inference is a
long-running, CPU/GPU-bound loop, and coupling it to the web server would
block request handling and make horizontal scaling (NFR-04) awkward. In
docker-compose.yml this maps to a `worker` service; in Kubernetes it would
be one Deployment/pod per camera or a pool of workers pulling camera
assignments from a queue.

Nothing in this file is executed in the sandbox (no camera, no GPU, no
running Postgres/Redis) — it's included so the wiring between the services
above is explicit and reviewable, matching how it would run in production.
"""
import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml.model_registry import get_active_detector
from app.ml.yolo_wrapper import non_max_suppression
from app.models.camera import CameraFeed
from app.models.detection_event import DetectionEvent
from app.models.zone import RiskZone
from app.services.alert_service import AlertService
from app.services.frame_preprocessor import FramePreprocessor
from app.services.risk_classifier import RiskClassifier
from app.services.tracker import GreedyIouTracker
from app.services.video_capture import VideoCaptureService

logger = logging.getLogger(__name__)
settings = get_settings()


class CameraPipeline:
    def __init__(self, camera: CameraFeed, zones: list[RiskZone], db: Session):
        self.camera = camera
        self.zones = zones
        self.db = db

        self.capture = VideoCaptureService(
    camera.source_uri,
    target_fps=camera.target_fps,
    loop=(camera.source_type == "file"),
)
        self.preprocessor = FramePreprocessor()
        self.detector = get_active_detector(db)
        self.tracker = GreedyIouTracker()
        self.classifier = RiskClassifier(
            safe_distance_m=settings.SAFE_DISTANCE_METERS,
            closing_speed_critical_mps=settings.CLOSING_SPEED_CRITICAL_MPS,
        )
        self.alert_service = AlertService(db)

        # Live pipeline-performance tracking (as opposed to a model card's
        # offline benchmark) — see _record_frame_latency().
        self._ema_latency_s: float | None = None
        self._frames_processed = 0
        self._metrics_flush_every = 30

    def _zone_for_point(self) -> RiskZone | None:
        # Simplification for the scaffold: one active zone per camera.
        # A multi-zone camera would test each polygon in risk_classifier.
        return self.zones[0] if self.zones else None

    def _record_frame_latency(self, elapsed_s: float) -> None:
        """
        Tracks measured single-image processing latency/FPS for this camera
        (preprocess + detect + track + classify + persist), smoothed with an
        exponential moving average and periodically flushed to CameraFeed so
        the dashboard reflects what this deployment is actually achieving —
        not just a claim about the model in isolation.
        """
        alpha = 0.1
        self._ema_latency_s = (
            elapsed_s if self._ema_latency_s is None else alpha * elapsed_s + (1 - alpha) * self._ema_latency_s
        )
        self._frames_processed += 1
        if self._frames_processed % self._metrics_flush_every == 0:
            self.camera.avg_processing_latency_ms = self._ema_latency_s * 1000.0
            self.camera.observed_fps = 1.0 / self._ema_latency_s if self._ema_latency_s > 0 else None
            self.db.commit()

    async def run(self) -> None:
        async for frame in self.capture.frames():
            frame_start = time.monotonic()

            lighting = self.preprocessor.estimate_lighting_condition(frame.image)
            threshold = (
                settings.LOW_LIGHT_CONFIDENCE_THRESHOLD
                if lighting == "low_light"
                else settings.DETECTION_CONFIDENCE_THRESHOLD
            )

            tensor, scale_x, scale_y = self.preprocessor.preprocess(frame.image)
            detections = self.detector.predict(tensor, confidence_threshold=threshold)  # FR-03/FR-04
            detections = non_max_suppression(detections)  # de-duplicate before tracking

            tracks = self.tracker.update(detections)  # FR-05

            zone = self._zone_for_point()
            for track in tracks:
                assessment = self.classifier.classify(
                    track, zone.polygon if zone else None, fps=self.camera.target_fps
                )  # FR-06/FR-07

                if track.occluded:
                    # No new visual evidence for this track this frame — the
                    # tracker is coasting on its last known position to
                    # bridge a brief occlusion (tracker.py). Logging a fresh
                    # DetectionEvent here would persist a stale duplicate;
                    # any alert already raised for this track_id remains the
                    # operative record until it's reacquired.
                    continue

                reasoning = {
                    **assessment.reasoning,
                    "lighting_condition": lighting,
                    "confidence_threshold_used": threshold,
                }

                event = DetectionEvent(
                    id=uuid.uuid4(),
                    camera_id=self.camera.id,
                    zone_id=zone.id if (zone and assessment.in_zone) else None,
                    track_id=track.track_id,
                    confidence=track.bbox.confidence,
                    bbox={"x1": track.bbox.x1, "y1": track.bbox.y1, "x2": track.bbox.x2, "y2": track.bbox.y2},
                    distance_estimate_m=assessment.distance_estimate_m,
                    closing_speed_mps=assessment.closing_speed_mps,
                    classification=assessment.classification.value,
                    model_version=self.detector.weights_path,
                    reasoning=reasoning,
                )
                self.db.add(event)  # FR-09
                self.db.commit()
                self.db.refresh(event)

                self.alert_service.raise_alert_if_needed(event)  # FR-08

            self._record_frame_latency(time.monotonic() - frame_start)


async def run_all_active_cameras(db: Session) -> None:
    """Entry point for the `worker` process (see docker-compose.yml)."""
    cameras = db.query(CameraFeed).filter(CameraFeed.is_active.is_(True)).all()
    for camera in cameras:
        zones = db.query(RiskZone).filter(RiskZone.camera_id == camera.id).all()
        pipeline = CameraPipeline(camera, zones, db)
        logger.info("Starting pipeline for camera %s (%s)", camera.name, camera.id)
        await pipeline.run()  # in production, launch each as its own asyncio.Task
