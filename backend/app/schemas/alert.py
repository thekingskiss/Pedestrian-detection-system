import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    detection_event_id: uuid.UUID
    severity: str
    message: str
    created_at: datetime
    acknowledged: bool
    reasoning: dict | None = None


class AlertAcknowledge(BaseModel):
    acknowledged: bool = True


class AlertRuleBase(BaseModel):
    camera_id: uuid.UUID | None = None
    confidence_threshold: float = 0.5
    low_light_confidence_threshold: float = 0.4
    safe_distance_meters: float = 3.0
    closing_speed_critical_mps: float = 2.0


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleOut(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    updated_at: datetime
