"""
FR-05: multi-object tracking so a pedestrian keeps the same identity
(track_id) across consecutive frames — needed for FR-06/FR-07's distance and
closing-speed estimates, which are meaningless for a single, unlinked frame.

A production deployment would use ByteTrack or DeepSORT (both integrate
directly with Ultralytics). This is a minimal greedy IoU-matching tracker:
same interface and output shape as a real tracker, so it's a drop-in
replacement point rather than a placeholder that would need restructuring.
"""
from dataclasses import dataclass, field

from app.ml.yolo_wrapper import Detection, iou


@dataclass
class Track:
    track_id: int
    bbox: Detection
    age: int = 0
    occluded: bool = False
    history: list[Detection] = field(default_factory=list)


class GreedyIouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 10):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Track]:
        unmatched_detections = list(detections)
        matched_track_ids: set[int] = set()

        for track_id, track in self._tracks.items():
            if not unmatched_detections:
                break
            best_iou, best_det = 0.0, None
            for det in unmatched_detections:
                score = iou(track.bbox, det)
                if score > best_iou:
                    best_iou, best_det = score, det

            if best_det is not None and best_iou >= self.iou_threshold:
                track.bbox = best_det
                track.age = 0
                track.occluded = False
                track.history.append(best_det)
                unmatched_detections.remove(best_det)
                matched_track_ids.add(track_id)

        # age out unmatched tracks (handles brief occlusion — cf. test T-05).
        # `occluded=True` tells downstream stages (risk_classifier,
        # pipeline_orchestrator) that this frame has no new visual evidence
        # for the track, just a coasted last-known position.
        for track_id, track in list(self._tracks.items()):
            if track_id not in matched_track_ids:
                track.occluded = True
                track.age += 1
                if track.age > self.max_age:
                    del self._tracks[track_id]

        # spawn new tracks for anything left unmatched
        for det in unmatched_detections:
            track = Track(track_id=self._next_id, bbox=det, occluded=False, history=[det])
            self._tracks[self._next_id] = track
            self._next_id += 1

        return list(self._tracks.values())
