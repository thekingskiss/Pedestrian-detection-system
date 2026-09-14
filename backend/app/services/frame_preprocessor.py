"""
FR-02: resize, normalise, and otherwise prepare each captured frame for
input into the YOLO detection model.
"""
import cv2
import numpy as np


class FramePreprocessor:
    def __init__(self, input_size: tuple[int, int] = (640, 640)):
        self.input_size = input_size

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, float]:
        """
        Letterbox-resizes `image` to `self.input_size` and scales pixel
        values to [0, 1]. Returns (tensor_ready_array, scale_x, scale_y) so
        callers can map model-space bounding boxes back to original-frame
        coordinates.
        """
        original_h, original_w = image.shape[:2]
        target_w, target_h = self.input_size

        resized = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalised = rgb.astype(np.float32) / 255.0

        scale_x = original_w / target_w
        scale_y = original_h / target_h
        return normalised, scale_x, scale_y

    def estimate_lighting_condition(self, image: np.ndarray) -> str:
        """
        Cheap heuristic (mean luma) used to pick between
        DETECTION_CONFIDENCE_THRESHOLD and LOW_LIGHT_CONFIDENCE_THRESHOLD —
        supports test criterion T-02 (low-light detection at a relaxed
        confidence threshold).
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_luma = float(np.mean(gray))
        return "low_light" if mean_luma < 60.0 else "normal"
