from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.detection_event import DetectionEvent
from app.schemas.detection import DetectionEventFilter, DetectionEventOut

router = APIRouter()


@router.get("/", response_model=list[DetectionEventOut])
def list_detections(
    filters: DetectionEventFilter = Depends(),
    db: Session = Depends(get_db),
) -> list[DetectionEvent]:
    """
    Read path for FR-09 logged events / FR-10 dashboard drill-down.
    Detection *writes* happen out-of-band via the pipeline orchestrator
    (services/pipeline_orchestrator.py), not through this HTTP API — that
    keeps the hot inference loop off the request/response cycle.
    """
    query = db.query(DetectionEvent)

    if filters.camera_id:
        query = query.filter(
            DetectionEvent.camera_id == filters.camera_id
        )

    if filters.classification:
        query = query.filter(
            DetectionEvent.classification == filters.classification
        )

    if filters.start:
        query = query.filter(
            DetectionEvent.timestamp >= filters.start
        )

    if filters.end:
        query = query.filter(
            DetectionEvent.timestamp <= filters.end
        )

    if filters.source_start is not None:
        query = query.filter(
            DetectionEvent.source_timestamp >= filters.source_start
        )

    if filters.source_end is not None:
        query = query.filter(
            DetectionEvent.source_timestamp <= filters.source_end
        )

    return (
        query.order_by(DetectionEvent.timestamp.desc())
        .offset(filters.offset)
        .limit(min(filters.limit, 500))
        .all()
    )