from datetime import datetime
from typing import Optional, List, Literal
import re
from pydantic import EmailStr, field_validator, model_validator
from app.schemas.base import BaseSchema

RoleType = Literal["ADMIN", "PERSONNEL", "ENSEIGNANT", "ETUDIANT"]
LevelType = Literal["L1", "L2", "L3", "M1", "M2"]
TrackType = Literal["GB", "SR", "IG"]


class UserSummary(BaseSchema):
    id: int
    first_name: str
    last_name: str
    email: str
    role: RoleType
    avatar_url: Optional[str] = None


class UserBase(BaseSchema):
    matricule: str
    first_name: str
    last_name: str
    email: EmailStr
    role: RoleType
    level: Optional[LevelType] = None
    track: Optional[TrackType] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    signature: Optional[str] = None
    notif_email: bool = True
    active: bool = True


class UserCreate(UserBase):
    password: Optional[str] = None


class UserPayload(BaseSchema):
    matricule: str
    first_name: str
    last_name: str
    email: EmailStr
    role: RoleType
    level: Optional[LevelType] = None
    track: Optional[TrackType] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    active: bool = True


class UserStatusUpdate(BaseSchema):
    active: bool


class RegisterPayload(BaseSchema):
    role: RoleType
    first_name: str
    last_name: str
    email: EmailStr  # e-mail ENI (@eni.mg)
    email_verification: EmailStr  # e-mail externe qui reçoit les codes OTP
    phone: str
    matricule: str
    password: str
    # Étudiant
    level: Optional[LevelType] = None
    track: Optional[TrackType] = None
    enrollment_year: Optional[str] = None
    # Enseignant
    teacher_status: Optional[str] = None
    specialty: Optional[str] = None
    levels_taught: Optional[List[str]] = None
    # Personnel / Administrateur
    department: Optional[str] = None
    position: Optional[str] = None
    justification: Optional[str] = None
    sponsor_email: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        # RG12 : 12 caractères minimum, une majuscule, un chiffre et un symbole
        if len(v) < 12 or not re.search(r"[A-Z]", v) or not re.search(r"\d", v) or not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("12 caractères minimum, une majuscule, un chiffre et un symbole (RG12)")
        return v

    @model_validator(mode="after")
    def email_verification_distinct(self):
        if self.email_verification.strip().lower() == self.email.strip().lower():
            raise ValueError(
                "L'e-mail de vérification doit être différent de l'e-mail ENI."
            )
        return self


class UserUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    signature: Optional[str] = None
    notif_email: Optional[bool] = None
    position: Optional[str] = None
    active: Optional[bool] = None
    level: Optional[LevelType] = None
    track: Optional[TrackType] = None


class UserResponse(BaseSchema):
    id: int
    matricule: str
    first_name: str
    last_name: str
    email: str
    role: RoleType
    level: Optional[str] = None
    track: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    signature: Optional[str] = None
    notif_email: bool = True
    avatar_url: Optional[str] = None
    active: bool = True
    pending: bool = False
    is_verified: bool = True
    created_at: datetime
    last_login_at: Optional[datetime] = None
