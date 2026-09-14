"""
FR-01: video/frame capture from a connected camera, CCTV RTSP stream, or an
uploaded video file.

Wraps OpenCV's VideoCapture behind an async generator so the rest of the
pipeline (preprocessing, inference, tracking) doesn't need to know whether
frames are coming from a live RTSP feed or a recorded file — both are just
"the next frame".
"""
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Frame:
    index: int
    timestamp: float
    image: np.ndarray  # BGR, as returned by OpenCV


class VideoCaptureService:
    def __init__(self, source_uri: str, target_fps: int = 15):
        self.source_uri = source_uri
        self.target_fps = target_fps
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self.source_uri)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video source: {self.source_uri}")

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    async def frames(self) -> AsyncIterator[Frame]:
        """
        Yields frames at approximately `target_fps`, regardless of the
        source's native rate — supports NFR-01 (>=15 FPS processing) without
        wasting inference cycles on a higher-rate source.
        """
        if self._cap is None:
            self.open()

        native_fps = self._cap.get(cv2.CAP_PROP_FPS) or self.target_fps
        stride = max(1, round(native_fps / self.target_fps))

        index = 0
        while True:
            ok, image = self._cap.read()
            if not ok:
                break  # end of file, or transient camera-feed interruption (NFR-03)

            if index % stride == 0:
                timestamp = self._cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                yield Frame(index=index, timestamp=timestamp, image=image)
                # Cooperative yield so this coroutine doesn't starve the
                # event loop when running inline with the FastAPI process.
                await asyncio.sleep(0)

            index += 1

        self.close()
