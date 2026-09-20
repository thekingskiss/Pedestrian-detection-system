from dataclasses import dataclass
from enum import Enum

from app.ml.yolo_wrapper import Detection
from app.services.tracker import Track


class Classification(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    classification: Classification
    in_zone: bool
    distance_estimate_m: float | None
    closing_speed_mps: float | None
    reasoning: dict


def point_in_polygon(
    x: float,
    y: float,
    polygon: list[tuple[float, float]],
) -> bool:
    inside = False

    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        intersects = (
            ((yi > y) != (yj > y))
            and (
                x
                < (xj - xi) * (y - yi) / (yj - yi + 1e-12)
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def bbox_center(bbox: Detection) -> tuple[float, float]:
    return (
        (bbox.x1 + bbox.x2) / 2,
        (bbox.y1 + bbox.y2) / 2,
    )


def estimate_distance_m(bbox: Detection) -> float:
    """
    Simple normalized bounding-box based distance estimate.

    Larger pedestrian bounding boxes generally indicate a person
    is closer to the camera.
    """

    height = max(bbox.y2 - bbox.y1, 1e-6)

    return 1.0 / height


def estimate_closing_speed_mps(
    track: Track,
    fps: float,
) -> float | None:
    if len(track.history) < 2:
        return None

    previous = track.history[-2]
    current = track.history[-1]

    previous_height = previous.y2 - previous.y1
    current_height = current.y2 - current.y1

    if previous_height <= 0 or current_height <= 0:
        return None

    growth = current_height - previous_height

    return max(0.0, growth * fps)


class RiskClassifier:
    def __init__(
        self,
        safe_distance_m=3.0,
        closing_speed_critical_mps=2.0,
    ):
        self.safe_distance_m = safe_distance_m
        self.closing_speed_critical_mps = closing_speed_critical_mps

    def classify(
        self,
        track: Track,
        zone_polygon,
        fps: float,
    ) -> RiskAssessment:

        cx, cy = bbox_center(track.bbox)

        in_zone = (
            zone_polygon is not None
            and point_in_polygon(cx, cy, zone_polygon)
        )

        distance = estimate_distance_m(track.bbox)

        closing_speed = estimate_closing_speed_mps(
            track,
            fps,
        )

        if in_zone and (
            closing_speed is not None
            and closing_speed >= self.closing_speed_critical_mps
        ):
            classification = Classification.CRITICAL

        elif in_zone:
            classification = Classification.CAUTION

        else:
            classification = Classification.SAFE

        reasoning = {
            "in_zone": in_zone,
            "distance_estimate_m": distance,
            "closing_speed_mps": closing_speed,
            "safe_distance_m": self.safe_distance_m,
            "closing_speed_critical_mps": (
                self.closing_speed_critical_mps
            ),
        }

        return RiskAssessment(
            classification=classification,
            in_zone=in_zone,
            distance_estimate_m=distance,
            closing_speed_mps=closing_speed,
            reasoning=reasoning,
        )