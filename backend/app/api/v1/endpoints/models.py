import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.security import Role
from app.models.model_version import ModelVersion
from app.schemas.dashboard import ModelVersionCreate, ModelVersionOut

router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


@router.get("/", response_model=list[ModelVersionOut])
def list_model_versions(db: Session = Depends(get_db)) -> list[ModelVersion]:
    return db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()


@router.post("/", response_model=ModelVersionOut, status_code=status.HTTP_201_CREATED)
def register_model_version(payload: ModelVersionCreate, db: Session = Depends(get_db)) -> ModelVersion:
    """
    FR-13: registers a newly (re)trained weight artifact. Registration alone
    does not make it live — see /activate, which is a separate, explicit
    step so a bad retrain can't silently take over the production pipeline.
    """
    version = ModelVersion(**payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.post("/{model_id}/activate", response_model=ModelVersionOut)
def activate_model_version(model_id: uuid.UUID, db: Session = Depends(get_db)) -> ModelVersion:
    version = db.get(ModelVersion, model_id)
    if not version:
        raise HTTPException(status_code=404, detail="Model version not found")

    db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).update({"is_active": False})
    version.is_active = True
    db.commit()
    db.refresh(version)
    # In a real deployment this would also signal the running inference
    # workers (via Redis pub/sub) to hot-swap weights — see
    # app/ml/model_registry.py::reload_active_model().
    return version
