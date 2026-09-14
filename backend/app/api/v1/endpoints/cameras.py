import uuid

from fastapi import APIRouter, Depends, HTTPException, status
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
