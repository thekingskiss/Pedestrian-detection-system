from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.alert import Alert
from app.models.camera import CameraFeed
from app.models.detection_event import DetectionEvent
from app.models.zone import RiskZone
from app.schemas.dashboard import DashboardSummary, HotspotEntry

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    hours: int = Query(24, ge=1, le=24 * 30), db: Session = Depends(get_db)
) -> DashboardSummary:
    """
    FR-10: single aggregate payload for the officer-facing dashboard —
    detection counts, hotspots, and alert history summarised over a window.
    """
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=hours)

    total_detections = (
        db.query(func.count(DetectionEvent.id))
        .filter(DetectionEvent.timestamp.between(window_start, window_end))
        .scalar()
    ) or 0

    total_critical = (
        db.query(func.count(Alert.id))
        .filter(Alert.severity == "critical", Alert.created_at.between(window_start, window_end))
        .scalar()
    ) or 0

    total_caution = (
        db.query(func.count(Alert.id))
        .filter(Alert.severity == "caution", Alert.created_at.between(window_start, window_end))
        .scalar()
    ) or 0

    active_cameras = db.query(func.count(CameraFeed.id)).filter(CameraFeed.is_active.is_(True)).scalar() or 0

    # Live pipeline performance, averaged across active cameras that have
    # reported at least one metrics window (see CameraPipeline._record_frame_latency
    # in pipeline_orchestrator.py) — NULL until a worker has actually run.
    avg_latency_ms = (
        db.query(func.avg(CameraFeed.avg_processing_latency_ms))
        .filter(CameraFeed.is_active.is_(True), CameraFeed.avg_processing_latency_ms.isnot(None))
        .scalar()
    )
    avg_fps = (
        db.query(func.avg(CameraFeed.observed_fps))
        .filter(CameraFeed.is_active.is_(True), CameraFeed.observed_fps.isnot(None))
        .scalar()
    )

    hotspot_rows = (
        db.query(
            DetectionEvent.zone_id,
            RiskZone.name,
            DetectionEvent.camera_id,
            CameraFeed.name,
            func.count(DetectionEvent.id).label("detection_count"),
            func.sum(
                case((DetectionEvent.classification == "critical", 1), else_=0)
            ).label("critical_count"),
        )
        .join(CameraFeed, CameraFeed.id == DetectionEvent.camera_id)
        .outerjoin(RiskZone, RiskZone.id == DetectionEvent.zone_id)
        .filter(DetectionEvent.timestamp.between(window_start, window_end))
        .group_by(DetectionEvent.zone_id, RiskZone.name, DetectionEvent.camera_id, CameraFeed.name)
        .order_by(func.count(DetectionEvent.id).desc())
        .limit(10)
        .all()
    )

    hotspots = [
        HotspotEntry(
            zone_id=row[0],
            zone_name=row[1],
            camera_id=row[2],
            camera_name=row[3],
            detection_count=row[4],
            critical_count=row[5] or 0,
        )
        for row in hotspot_rows
    ]

    return DashboardSummary(
        window_start=window_start,
        window_end=window_end,
        total_detections=total_detections,
        total_critical_alerts=total_critical,
        total_caution_alerts=total_caution,
        active_cameras=active_cameras,
        hotspots=hotspots,
        avg_processing_latency_ms=avg_latency_ms,
        avg_observed_fps=avg_fps,
    )
