"""
This module is the single boundary between "our system" and "the trained
YOLO model" (Section 7.2 / 7.3 of the write-up).

`YoloPedestrianDetector.predict()` calls a real, fine-tuned Ultralytics YOLO
model (see ml_training/train.py and ml_training/register_model.py for how
the active weights file gets produced and registered). The rest of the
codebase only depends on the `Detection` dataclass shape below.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    x1: float  # normalised [0,1] frame-space coordinates
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int = 0  # 0 = "person" in COCO-derived class maps


def iou(a: Detection, b: Detection) -> float:
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _containment_ratio(inner: Detection, outer: Detection) -> float:
    """Fraction of `inner`'s area that overlaps `outer`."""
    ix1, iy1 = max(inner.x1, outer.x1), max(inner.y1, outer.y1)
    ix2, iy2 = min(inner.x2, outer.x2), min(inner.y2, outer.y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    inner_area = max((inner.x2 - inner.x1) * (inner.y2 - inner.y1), 1e-9)
    return inter / inner_area


def non_max_suppression(
    detections: list[Detection],
    containment_threshold: float = 0.8,
) -> list[Detection]:
    """
    FR-03/FR-04: de-duplicates raw per-frame detections before they reach the
    tracker. Plain IoU-based NMS can't always tell a duplicate box on one
    pedestrian from a legitimate box on a second pedestrian standing close
    to them, and in crowded scenes that discards real detections alongside
    the redundant ones — high IoU alone isn't a reliable duplicate signal,
    since two boxes of very different size (e.g. a real detection and a
    small spurious box nested inside it) can have low IoU despite one being
    entirely covered by the other.

    A candidate is suppressed once most of its *own* area is already covered
    by an already-kept, higher-confidence box — whether that's a
    near-identical duplicate on the same pedestrian or a smaller spurious box
    nested inside a real one. Two pedestrians standing close together produce
    boxes that overlap substantially without either one's area being mostly
    covered by the other, so both survive: neither looks like "a second
    guess at the same target" from its own point of view.
    """
    ordered = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    for candidate in ordered:
        is_duplicate = any(
            _containment_ratio(candidate, kept_box) >= containment_threshold for kept_box in kept
        )
        if not is_duplicate:
            kept.append(candidate)
    return kept


class YoloPedestrianDetector:
    """Thin wrapper around an Ultralytics YOLO model, fine-tuned for pedestrians."""

    def __init__(self, weights_path: str):
        self.weights_path = weights_path
        self._model = None  # lazily loaded; see load()

    def load(self) -> None:
        from ultralytics import YOLO

        self._model = YOLO(self.weights_path)

    def predict(self, image: np.ndarray, confidence_threshold: float) -> list[Detection]:
        """
        FR-03/FR-04: runs pedestrian detection + confidence filtering.
        """
        if self._model is None:
            self.load()

        results = self._model.predict(image, conf=confidence_threshold, verbose=False)[0]
        print(
            f"DEBUG: raw model output — {len(results.boxes)} boxes at conf>={confidence_threshold}",
            flush=True,
        )
        return [
            Detection(
                *box.xyxyn[0].tolist(),
                confidence=float(box.conf[0]),
                class_id=int(box.cls[0]),
            )
            for box in results.boxes
        ]
