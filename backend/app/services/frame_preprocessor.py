"""
FR-02: resize and prepare each captured frame for
input into the YOLO detection model.
"""
import cv2
import numpy as np


class FramePreprocessor:
    def __init__(self, input_size: tuple[int, int] = (640, 640)):
        self.input_size = input_size

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, float]:
        """
        Resize the frame and prepare it for YOLO.
        Returns (tensor_ready_array, scale_x, scale_y).
        """
        original_h, original_w = image.shape[:2]
        target_w, target_h = self.input_size

        resized = cv2.resize(
            image,
            (target_w, target_h),
            interpolation=cv2.INTER_LINEAR,
        )

        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        scale_x = original_w / target_w
        scale_y = original_h / target_h

        return rgb, scale_x, scale_y

    def estimate_lighting_condition(self, image: np.ndarray) -> str:
        """
        Cheap heuristic (mean luma) used to pick between
        DETECTION_CONFIDENCE_THRESHOLD and LOW_LIGHT_CONFIDENCE_THRESHOLD.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_luma = float(np.mean(gray))
        return "low_light" if mean_luma < 60.0 else "normal"