import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.security import Role
from app.models.zone import RiskZone
from app.schemas.zone import ZoneCreate, ZoneOut, ZoneUpdate

router = APIRouter()


@router.get("/", response_model=list[ZoneOut])
def list_zones(camera_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[RiskZone]:
    query = db.query(RiskZone)
    if camera_id:
        query = query.filter(RiskZone.camera_id == camera_id)
    return query.all()


@router.post(
    "/",
    response_model=ZoneOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)) -> RiskZone:
    zone = RiskZone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch(
    "/{zone_id}",
    response_model=ZoneOut,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def update_zone(zone_id: uuid.UUID, payload: ZoneUpdate, db: Session = Depends(get_db)) -> RiskZone:
    zone = db.get(RiskZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
def delete_zone(zone_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    zone = db.get(RiskZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(zone)
    db.commit()
