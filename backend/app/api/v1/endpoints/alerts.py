import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.security import Role
from app.models.alert import Alert, AlertRule
from app.models.user import User
from app.schemas.alert import AlertAcknowledge, AlertOut, AlertRuleCreate, AlertRuleOut

router = APIRouter()


@router.get("/", response_model=list[AlertOut])
def list_alerts(
    acknowledged: bool | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Alert]:
    query = db.query(Alert)
    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)
    if severity:
        query = query.filter(Alert.severity == severity)
    return query.order_by(Alert.created_at.desc()).limit(min(limit, 500)).all()


@router.patch("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: uuid.UUID,
    payload: AlertAcknowledge,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = payload.acknowledged
    alert.acknowledged_by = current_user.id if payload.acknowledged else None
    db.commit()
    db.refresh(alert)
    return alert


# --- FR-11: alert-rule / threshold configuration ---------------------------

rules_router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


@rules_router.get("/", response_model=list[AlertRuleOut])
def list_alert_rules(db: Session = Depends(get_db)) -> list[AlertRule]:
    return db.query(AlertRule).all()


@rules_router.post("/", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)) -> AlertRule:
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
