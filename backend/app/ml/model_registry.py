"""
FR-13: resolves which trained weight artifact is currently active and hands
back a loaded YoloPedestrianDetector. Kept separate from yolo_wrapper.py so
"which weights to use" (a DB-driven decision, changeable via
POST /models/{id}/activate) is decoupled from "how to run inference".
"""
from sqlalchemy.orm import Session

from app.ml.yolo_wrapper import YoloPedestrianDetector
from app.models.model_version import ModelVersion

_cached_detector: YoloPedestrianDetector | None = None
_cached_weights_path: str | None = None


def get_active_detector(db: Session) -> YoloPedestrianDetector:
    global _cached_detector, _cached_weights_path

    active = db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).first()
    if active is None:
        raise RuntimeError("No active model version configured — register and activate one first.")

    if _cached_detector is None or _cached_weights_path != active.weights_path:
        _cached_detector = YoloPedestrianDetector(active.weights_path)
        _cached_detector.load()
        _cached_weights_path = active.weights_path

    return _cached_detector


def reload_active_model(db: Session) -> None:
    """Force a reload on the next get_active_detector() call — used after activation."""
    global _cached_detector
    _cached_detector = None
