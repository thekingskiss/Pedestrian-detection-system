import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.security import Role
from app.models.camera import CameraFeed
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate

router = APIRouter()


@router.get("/", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)) -> list[CameraFeed]:
    return db.query(CameraFeed).order_by(CameraFeed.created_at.desc()).all()


@router.post(
    "/",
    response_model=CameraOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)) -> CameraFeed:
    """
    NFR-04: adding a camera/detection node is a single insert — the pipeline
    orchestrator (services/pipeline_orchestrator.py) discovers active cameras
    at poll time rather than requiring a redeploy.
    """
    camera = CameraFeed(**payload.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.patch(
    "/{camera_id}",
    response_model=CameraOut,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def update_camera(camera_id: uuid.UUID, payload: CameraUpdate, db: Session = Depends(get_db)) -> CameraFeed:
    camera = db.get(CameraFeed, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def delete_camera(camera_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    camera = db.get(CameraFeed, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()

UPLOAD_DIR = Path("/data/sample_clips/uploads")


@router.post(
    "/{camera_id}/video",
    response_model=CameraOut,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def upload_camera_video(
    camera_id: uuid.UUID, file: UploadFile, db: Session = Depends(get_db)
) -> CameraFeed:
    """
    Lets an admin upload a video clip from the dashboard and immediately
    point this camera at it — the persistent worker (see app/worker.py)
    picks up the change on its next poll pass, so this is the fastest path
    to testing detection end-to-end without a live RTSP feed.
    """
    camera = db.get(CameraFeed, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest_filename = f"{camera_id}_{file.filename}"
    dest_path = UPLOAD_DIR / dest_filename
    with dest_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    camera.source_type = "upload"
    camera.source_uri = f"/data/sample_clips/uploads/{dest_filename}"
    camera.is_active = True
    db.commit()
    db.refresh(camera)
    return camera
