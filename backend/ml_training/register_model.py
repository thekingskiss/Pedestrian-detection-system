"""
Registers the fine-tuned weights (ml_training/train.py's output,
benchmarked by ml_training/evaluate.py) as a new ModelVersion row and
activates it, so the running API picks it up on its next
get_active_detector() call (see app/ml/model_registry.py).

Run: python ml_training/evaluate.py   # note the printed metrics dict
     python ml_training/l.py --map50 0.xx --map50-95 0.xx --latency-ms 0.xx --fps 0.xx
"""
import argparse

from app.db.session import SessionLocal
from app.models.model_version import ModelVersion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map50", type=float, required=True)
    parser.add_argument("--map50-95", type=float, required=True)
    parser.add_argument("--latency-ms", type=float, required=True)
    parser.add_argument("--fps", type=float, required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).update({"is_active": False})

        version = ModelVersion(
            name="yolov8n-pedestrian-v2",
            weights_path="/models/yolov8n-pedestrian-v2.pt",
            trained_on="Train/Test/Val pedestrian dataset (Pascal VOC, person + person-like), "
            "fine-tuned from COCO-pretrained yolov8n.pt",
            map50=args.map50,
            map50_95=args.map50_95,
            avg_inference_latency_ms=args.latency_ms,
            benchmark_fps=args.fps,
            latency_type="single_image",
            latency_hardware="CPU (4 cores, no GPU)",
            is_active=True,
        )
        db.add(version)
        db.commit()
        print(f"Registered and activated ModelVersion {version.id} ({version.name})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
