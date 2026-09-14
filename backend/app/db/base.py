from app.db.base_class import Base

# Import all models here so Alembic's autogenerate can discover them via
# Base.metadata. Individual model modules import Base from app.db.base_class
# (not from this module) to avoid a circular import.
from app.models.user import User  # noqa: E402,F401
from app.models.camera import CameraFeed  # noqa: E402,F401
from app.models.zone import RiskZone  # noqa: E402,F401
from app.models.detection_event import DetectionEvent  # noqa: E402,F401
from app.models.alert import Alert, AlertRule  # noqa: E402,F401
from app.models.model_version import ModelVersion  # noqa: E402,F401
