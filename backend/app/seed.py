"""
Seeds a first admin account plus a demo camera/zone/model-version so the
frontend has something to render on first run.

    python -m app.seed

Not executed in this sandbox (no live Postgres). Idempotent: re-running
skips rows that already exist by unique key.
"""
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.camera import CameraFeed
from app.models.model_version import ModelVersion
from app.models.user import User
from app.models.zone import RiskZone


def seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@pds.local").first():
            db.add(
                User(
                    email="admin@pds.local",
                    full_name="System Administrator",
                    hashed_password=hash_password("change-me-on-first-login"),
                    role="admin",
                )
            )

        camera = db.query(CameraFeed).filter(CameraFeed.name == "Demo Crossing — Ring Road").first()
        if not camera:
            camera = CameraFeed(
                name="Demo Crossing — Ring Road",
                source_type="file",
                source_uri="/data/sample_clips/ring_road_demo.mp4",
                location_label="Ring Road / Achimota Interchange, Accra",
                latitude=5.6108,
                longitude=-0.2199,
                target_fps=15,
            )
            db.add(camera)
            db.flush()  # get camera.id before referencing it below

        if not db.query(RiskZone).filter(RiskZone.camera_id == camera.id).first():
            db.add(
                RiskZone(
                    camera_id=camera.id,
                    name="Marked crossing",
                    polygon=[[0.3, 0.6], [0.7, 0.6], [0.75, 0.95], [0.25, 0.95]],
                    safe_distance_meters=3.0,
                )
            )

        if not db.query(ModelVersion).filter(ModelVersion.name == "yolov8n-pedestrian-v1").first():
            db.add(
                ModelVersion(
                    name="yolov8n-pedestrian-v1",
                    weights_path="/models/yolov8n-pedestrian-v1.pt",
                    trained_on="COCO pretrain + Caltech Pedestrian + CityPersons (fine-tune)",
                    map50=0.0,  # placeholder until a real training run populates this
                    map50_95=0.0,
                    is_active=True,
                )
            )

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
