"""
Fine-tunes a YOLOv8n checkpoint on the converted pedestrian dataset
(ml_training/dataset/, produced by convert_voc_to_yolo.py) and copies the
resulting weights into MODEL_WEIGHTS_DIR (backend/.env) as
yolov8n-pedestrian-v2.pt, replacing the placeholder path the seeded
ModelVersion row points at.

CPU-only (no GPU in this environment): kept to a modest image size/epoch
count so a full run finishes in a reasonable time on 4 cores, not for peak
accuracy. See ml_training/evaluate.py for the real mAP this run achieves on
the held-out Test split.

Run: python ml_training/train.py
"""
from pathlib import Path

from ultralytics import YOLO

DATASET_YAML = Path(__file__).resolve().parent / "dataset" / "data.yaml"
RUNS_DIR = Path(__file__).resolve().parent / "runs"
WEIGHTS_OUT_DIR = Path(__file__).resolve().parents[1] / "models"

EPOCHS = 20
IMG_SIZE = 320
BATCH = 8


def main() -> None:
    WEIGHTS_OUT_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO("yolov8n.pt")  # COCO-pretrained starting point (transfer learning)
    model.train(
        data=str(DATASET_YAML),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        device="cpu",
        project=str(RUNS_DIR),
        name="pedestrian_finetune",
        exist_ok=True,
        patience=5,  # stop early if val loss stalls, given the short budget
        verbose=True,
    )

    best_weights = RUNS_DIR / "pedestrian_finetune" / "weights" / "best.pt"
    out_path = WEIGHTS_OUT_DIR / "yolov8n-pedestrian-v2.pt"
    out_path.write_bytes(best_weights.read_bytes())
    print(f"Copied {best_weights} -> {out_path}")


if __name__ == "__main__":
    main()
