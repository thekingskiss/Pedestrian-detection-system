"""
FR-08: generates a visual/audible alert when a Critical classification is
reached, and a lower-severity Caution notification otherwise (per the
Section 9 decision tree). Persists the Alert row (FR-09) and pushes it to
connected dashboard clients over the websocket channel (near-real-time,
matching test criterion T-08's 200ms target).

NFR-10: `dispatch_external` is the seam for pushing the same event to a
vehicle ADAS unit or municipal traffic-control system via a standard
API/message format (left as a documented extension point, not implemented,
since no such downstream system exists in this scaffold).
"""
import asyncio
import uuid

from sqlalchemy.orm import Session

from app.api.v1.endpoints.ws import publish_alert
from app.models.alert import Alert
from app.models.detection_event import DetectionEvent
from app.services.risk_classifier import Classification


def _message_for(classification: Classification, track_id: int, distance_m: float | None) -> str:
    if classification == Classification.CRITICAL:
        return f"CRITICAL: pedestrian (track #{track_id}) within safe distance, closing fast"
    return f"Caution: pedestrian (track #{track_id}) in risk zone at ~{distance_m:.1f}m"


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def raise_alert_if_needed(self, detection_event: DetectionEvent) -> Alert | None:
        if detection_event.classification not in (Classification.CAUTION, Classification.CRITICAL):
            return None

        alert = Alert(
            id=uuid.uuid4(),
            detection_event_id=detection_event.id,
            severity=detection_event.classification,
            message=_message_for(
                Classification(detection_event.classification),
                detection_event.track_id,
                detection_event.distance_estimate_m,
            ),
            reasoning=detection_event.reasoning,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        asyncio.create_task(
            publish_alert(
                {
                    "alert_id": str(alert.id),
                    "severity": alert.severity,
                    "message": alert.message,
                    "camera_id": str(detection_event.camera_id),
                    "created_at": alert.created_at,
                }
            )
        )

        self.dispatch_external(alert)  # NFR-10 seam
        return alert

    def dispatch_external(self, alert: Alert) -> None:
        """
        NFR-10: extension point for pushing to a vehicle ADAS unit or
        municipal traffic-control system. No-op in this scaffold — a real
        implementation would POST to a configured webhook URL per camera
        and set alert.dispatched_to_external accordingly.
        """
        return
