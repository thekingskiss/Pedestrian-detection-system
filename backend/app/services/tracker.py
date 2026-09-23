"""
FR-05: Multi-object pedestrian tracking.

This tracker keeps a stable track_id across consecutive detections while
always using the CURRENT YOLO detection bounding box for the active track.

Matching is performed globally by highest IoU first instead of iterating
through tracks one-by-one. This reduces identity switching when pedestrians
are close to each other.
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
    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_age: int = 10,
    ):
        self.iou_threshold = iou_threshold
        self.max_age = max_age

        self._tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Track]:
        """
        Match current YOLO detections to existing tracks.

        Important:
        - A matched track ALWAYS receives the current detection bbox.
        - We do NOT predict/coast a bbox and save it as a current detection.
        - Matching is performed globally using highest IoU first.
        """

        # ---------------------------------------------------------
        # 1. Build every possible track/detection IoU pair
        # ---------------------------------------------------------
        candidate_pairs: list[tuple[float, int, int]] = []

        track_ids = list(self._tracks.keys())

        for track_id in track_ids:
            track = self._tracks[track_id]

            for det_index, detection in enumerate(detections):
                score = iou(track.bbox, detection)

                if score >= self.iou_threshold:
                    candidate_pairs.append(
                        (score, track_id, det_index)
                    )

        # ---------------------------------------------------------
        # 2. Highest-IoU matches first
        #
        # This is better than:
        #   Track 1 -> first best detection
        #   Track 2 -> first remaining detection
        #
        # because the best overall matches get priority.
        # ---------------------------------------------------------
        candidate_pairs.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        matched_track_ids: set[int] = set()
        matched_detection_indices: set[int] = set()

        for score, track_id, det_index in candidate_pairs:
            if track_id in matched_track_ids:
                continue

            if det_index in matched_detection_indices:
                continue

            track = self._tracks.get(track_id)

            if track is None:
                continue

            detection = detections[det_index]

            # -----------------------------------------------------
            # IMPORTANT:
            # Replace the previous bbox with the CURRENT YOLO bbox.
            # -----------------------------------------------------
            track.bbox = detection
            track.age = 0
            track.occluded = False

            track.history.append(detection)

            # Keep history bounded.
            if len(track.history) > 30:
                track.history = track.history[-30:]

            matched_track_ids.add(track_id)
            matched_detection_indices.add(det_index)

        # ---------------------------------------------------------
        # 3. Age unmatched tracks
        #
        # These tracks are retained temporarily so that a pedestrian
        # can disappear briefly and keep the same track_id.
        #
        # The pipeline already checks occluded=True and does not save
        # a detection event for these coasted tracks.
        # ---------------------------------------------------------
        for track_id, track in list(self._tracks.items()):
            if track_id not in matched_track_ids:
                track.occluded = True
                track.age += 1

                if track.age > self.max_age:
                    del self._tracks[track_id]

        # ---------------------------------------------------------
        # 4. Create new tracks for detections that were not matched
        # ---------------------------------------------------------
        for det_index, detection in enumerate(detections):
            if det_index in matched_detection_indices:
                continue

            track = Track(
                track_id=self._next_id,
                bbox=detection,
                occluded=False,
                history=[detection],
            )

            self._tracks[self._next_id] = track
            self._next_id += 1

        # ---------------------------------------------------------
        # 5. Return every existing track.
        #
        # The orchestrator will ignore occluded tracks when saving
        # current-frame detection events.
        # ---------------------------------------------------------
        return list(self._tracks.values())