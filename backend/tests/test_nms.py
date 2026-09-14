"""
Unit tests for non_max_suppression() (app/ml/yolo_wrapper.py). Pure geometry
on Detection objects — no video/DB needed. Covers the two failure modes the
literature review flagged for plain IoU-based NMS in crowded scenes:
duplicate boxes on one pedestrian must be collapsed, but two distinct,
overlapping pedestrians must both survive.
"""
from app.ml.yolo_wrapper import Detection, non_max_suppression


def test_duplicate_boxes_are_suppressed():
    """Two near-identical boxes on the same pedestrian -> only the higher-confidence one survives."""
    high_conf = Detection(x1=0.40, y1=0.40, x2=0.60, y2=0.80, confidence=0.91)
    near_duplicate = Detection(x1=0.41, y1=0.41, x2=0.59, y2=0.79, confidence=0.62)

    kept = non_max_suppression([near_duplicate, high_conf])

    assert kept == [high_conf]


def test_distinct_overlapping_pedestrians_are_both_kept():
    """
    Two pedestrians standing close together produce boxes that overlap
    (shared IoU) without either containing the other -- plain greedy NMS
    would discard the lower-confidence one; the containment guard here
    should not, since neither box is mostly covered by the other.
    """
    left_pedestrian = Detection(x1=0.30, y1=0.40, x2=0.55, y2=0.80, confidence=0.88)
    right_pedestrian = Detection(x1=0.50, y1=0.40, x2=0.75, y2=0.80, confidence=0.79)

    kept = non_max_suppression([left_pedestrian, right_pedestrian])

    assert len(kept) == 2
    assert left_pedestrian in kept
    assert right_pedestrian in kept


def test_low_confidence_box_fully_inside_a_kept_box_is_suppressed():
    """A spurious small box entirely inside a real detection is a duplicate, not a second pedestrian."""
    real_detection = Detection(x1=0.20, y1=0.20, x2=0.80, y2=0.90, confidence=0.95)
    spurious_inner_box = Detection(x1=0.30, y1=0.30, x2=0.50, y2=0.50, confidence=0.40)

    kept = non_max_suppression([real_detection, spurious_inner_box])

    assert kept == [real_detection]


def test_non_overlapping_detections_are_all_kept():
    a = Detection(x1=0.0, y1=0.0, x2=0.1, y2=0.1, confidence=0.7)
    b = Detection(x1=0.5, y1=0.5, x2=0.6, y2=0.6, confidence=0.6)
    c = Detection(x1=0.9, y1=0.9, x2=1.0, y2=1.0, confidence=0.5)

    kept = non_max_suppression([a, b, c])

    assert len(kept) == 3
