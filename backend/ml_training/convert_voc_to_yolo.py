"""
One-off conversion of the Train/Test/Val Pascal-VOC-format pedestrian
dataset (Annotations/*.xml + JPEGImages/*.jpg, dropped in at the repo root)
into the images/ + labels/ layout Ultralytics YOLO expects, plus a data.yaml
pointing at it.

Classes: 0 = person, 1 = person-like (a distractor class in the source
dataset for silhouettes/statues/etc. that resemble a person — training on
it teaches the model to reject them; yolo_wrapper.py filters to class 0 at
inference, matching its documented `classes=[0]` real-model call).

Reads each image's actual dimensions via PIL rather than trusting the XML
<size> tag — one file in the Test split (`image (178)`) has a bogus 0x0
declared size while the JPEG itself is a normal 450x800, so trusting the
XML would corrupt every box in that file.

Run once: `python ml_training/convert_voc_to_yolo.py`
"""
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "dataset"

CLASS_IDS = {"person": 0, "person-like": 1}

SPLITS = {
    "train": REPO_ROOT / "Train" / "Train",
    "val": REPO_ROOT / "Val" / "Val",
    "test": REPO_ROOT / "Test" / "Test",
}


def convert_split(split_name: str, split_dir: Path) -> int:
    img_dir = split_dir / "JPEGImages"
    ann_dir = split_dir / "Annotations"

    images_out = OUT_DIR / "images" / split_name
    labels_out = OUT_DIR / "labels" / split_name
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    converted = 0
    for xml_path in sorted(ann_dir.glob("*.xml")):
        stem = xml_path.stem
        img_path = img_dir / f"{stem}.jpg"
        if not img_path.exists():
            continue

        with Image.open(img_path) as im:
            width, height = im.size

        root = ET.parse(xml_path).getroot()
        lines = []
        for obj in root.findall("object"):
            name = obj.findtext("name")
            class_id = CLASS_IDS.get(name)
            if class_id is None:
                continue

            bb = obj.find("bndbox")
            xmin = max(0.0, float(bb.findtext("xmin")))
            ymin = max(0.0, float(bb.findtext("ymin")))
            xmax = min(float(width), float(bb.findtext("xmax")))
            ymax = min(float(height), float(bb.findtext("ymax")))
            if xmax <= xmin or ymax <= ymin:
                continue  # degenerate box after clamping to actual image bounds

            x_center = (xmin + xmax) / 2.0 / width
            y_center = (ymin + ymax) / 2.0 / height
            box_w = (xmax - xmin) / width
            box_h = (ymax - ymin) / height
            lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}")

        # Symlinking would be faster but Windows requires elevated privileges
        # for symlinks; a plain copy keeps this portable.
        (images_out / f"{stem}.jpg").write_bytes(img_path.read_bytes())
        (labels_out / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        converted += 1

    return converted


def write_data_yaml() -> None:
    content = f"""\
path: {OUT_DIR.as_posix()}
train: images/train
val: images/val
test: images/test
names:
  0: person
  1: person-like
"""
    (OUT_DIR / "data.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    for split_name, split_dir in SPLITS.items():
        count = convert_split(split_name, split_dir)
        print(f"{split_name}: converted {count} images")
    write_data_yaml()
    print(f"Wrote {OUT_DIR / 'data.yaml'}")
