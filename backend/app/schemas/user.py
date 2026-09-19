import uuid
from datetime import datetime

import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr

# Officer/admin accounts here use internal-only addresses (e.g. admin@pds.local),
# which email_validator otherwise rejects as a reserved/special-use domain.
email_validator.SPECIAL_USE_DOMAIN_NAMES = []


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "officer"  # admin | officer | auditor


class UserCreate(UserBase):
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
