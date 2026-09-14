"""
Evaluates the fine-tuned weights (ml_training/train.py's output) on the
held-out Test split for real mAP@0.5 / mAP@0.5:0.95, and separately
benchmarks single-image CPU inference latency (as opposed to batched
throughput — see model_versions.latency_type / the literature review this
scaffold's README is built against, which is explicit that only
single-image latency supports a real-time claim).

Prints a Python dict so register_model.py (or a human) can consume the
numbers directly; doesn't touch the database itself.

Run: python ml_training/evaluate.py
"""
import time
from pathlib import Path

from ultralytics import YOLO

DATASET_YAML = Path(__file__).resolve().parent / "dataset" / "data.yaml"
WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "models" / "yolov8n-pedestrian-v2.pt"
BENCHMARK_RUNS = 20


def main() -> None:
    model = YOLO(str(WEIGHTS_PATH))

    metrics = model.val(data=str(DATASET_YAML), split="test", device="cpu", imgsz=320, verbose=False)
    map50 = float(metrics.box.map50)
    map50_95 = float(metrics.box.map)

    # Single-image latency: predict one at a time, discard the first (model
    # warmup/first-call overhead), average the rest.
    test_images_dir = Path(DATASET_YAML.parent / "images" / "test")
    sample_image = next(test_images_dir.glob("*.jpg"))

    latencies_s = []
    for i in range(BENCHMARK_RUNS + 1):
        start = time.perf_counter()
        model.predict(str(sample_image), device="cpu", imgsz=320, verbose=False)
        elapsed = time.perf_counter() - start
        if i > 0:  # discard warmup call
            latencies_s.append(elapsed)

    avg_latency_ms = (sum(latencies_s) / len(latencies_s)) * 1000.0
    fps = 1000.0 / avg_latency_ms

    result = {
        "map50": round(map50, 4),
        "map50_95": round(map50_95, 4),
        "avg_inference_latency_ms": round(avg_latency_ms, 2),
        "benchmark_fps": round(fps, 2),
    }
    print(result)


if __name__ == "__main__":
    main()
