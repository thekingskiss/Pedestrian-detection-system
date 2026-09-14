"""
FR-06/FR-07: implements the write-up's Section 9 decision tree verbatim:

    confidence < threshold?              -> discard (handled upstream, FR-04)
    outside risk zone?                   -> LOGGED_ONLY
    inside zone, beyond safe distance?   -> LOGGED_ONLY
    inside zone, within safe distance:
        closing speed > threshold m/s    -> CRITICAL
        closing speed <= threshold m/s   -> CAUTION

Distance/speed estimation here is a placeholder homography-free approximation
(bbox height as an inverse proxy for distance) — a real deployment would use
a calibrated camera homography or stereo/depth input. The important part for
this scaffold is that risk_classifier.py's *decision logic* is complete and
directly testable against the write-up's Table 10.2 test cases (T-07..T-09).
"""
from dataclasses import dataclass
from enum import Enum

from app.ml.yolo_wrapper import Detection
from app.services.tracker import Track


class Classification(str, Enum):
    SAFE = "safe"          # outside zone, or in zone but beyond safe distance
    CAUTION = "caution"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    classification: Classification
    in_zone: bool
    distance_estimate_m: float | None
    closing_speed_mps: float | None
    reasoning: dict  # audit trail: which rule fired and on what values (Section 5.6 XAI)


def point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    """Standard ray-casting point-in-polygon test; polygon is [[x,y], ...] normalised 0-1."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def bbox_center(bbox: Detection) -> tuple[float, float]:
    return (bbox.x1 + bbox.x2) / 2.0, bbox.y2  # use bottom-center as ground contact point


def estimate_distance_m(bbox: Detection, reference_bbox_height: float = 0.35) -> float:
    """
    Placeholder monocular distance heuristic: a pedestrian's bbox height in
    a calibrated frame is roughly inversely proportional to distance.
    `reference_bbox_height` is the normalised bbox height of a pedestrian
    known to be ~3m away, tuned per camera during zone setup (FR-11).
    """
    bbox_height = max(bbox.y2 - bbox.y1, 1e-6)
    return 3.0 * (reference_bbox_height / bbox_height)


def estimate_closing_speed_mps(track: Track, fps: float) -> float:
    """Finite-difference speed estimate from the last two bbox heights in the track's history."""
    if len(track.history) < 2:
        return 0.0
    prev_dist = estimate_distance_m(track.history[-2])
    curr_dist = estimate_distance_m(track.history[-1])
    dt = 1.0 / fps if fps > 0 else 1.0 / 15.0
    # positive = closing (getting nearer)
    return max(0.0, (prev_dist - curr_dist) / dt)


class RiskClassifier:
    def __init__(
        self,
        safe_distance_m: float = 3.0,
        closing_speed_critical_mps: float = 2.0,
    ):
        self.safe_distance_m = safe_distance_m
        self.closing_speed_critical_mps = closing_speed_critical_mps

    def classify(
        self,
        track: Track,
        zone_polygon: list[list[float]] | None,
        fps: float,
    ) -> RiskAssessment:
        cx, cy = bbox_center(track.bbox)
        in_zone = zone_polygon is not None and point_in_polygon(cx, cy, zone_polygon)

        base_reasoning = {
            "in_zone": in_zone,
            "occluded": track.occluded,
            "safe_distance_m": self.safe_distance_m,
            "closing_speed_critical_mps": self.closing_speed_critical_mps,
        }

        if not in_zone:
            reasoning = {**base_reasoning, "rule_fired": "outside_risk_zone"}
            return RiskAssessment(Classification.SAFE, in_zone, None, None, reasoning)

        distance = estimate_distance_m(track.bbox)
        if distance > self.safe_distance_m:
            reasoning = {**base_reasoning, "rule_fired": "beyond_safe_distance", "distance_estimate_m": distance}
            return RiskAssessment(Classification.SAFE, in_zone, distance, None, reasoning)

        closing_speed = estimate_closing_speed_mps(track, fps)
        classification = (
            Classification.CRITICAL
            if closing_speed > self.closing_speed_critical_mps
            else Classification.CAUTION
        )
        reasoning = {
            **base_reasoning,
            "rule_fired": "closing_speed_exceeded" if classification == Classification.CRITICAL else "in_zone_slow_approach",
            "distance_estimate_m": distance,
            "closing_speed_mps": closing_speed,
        }
        return RiskAssessment(classification, in_zone, distance, closing_speed, reasoning)
