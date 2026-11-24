from datetime import datetime
from typing import Optional, List, Dict
from pydantic import Field
from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary, RoleType


class AuditLogResponse(BaseSchema):
    id: int
    user: Optional[UserSummary] = None
    action: str
    details: str = ""
    ip: Optional[str] = None
    date: datetime


class UserStats(BaseSchema):
    total: int = 0
    active: int = 0
    by_role: Dict[RoleType, int] = Field(
        default_factory=lambda: {
            "ADMIN": 0,
            "PERSONNEL": 0,
            "ENSEIGNANT": 0,
            "ETUDIANT": 0,
        }
    )


class ActivityStat(BaseSchema):
    date: str
    count: int


class TopSenderStat(BaseSchema):
    user: UserSummary
    count: int


class AdminStats(BaseSchema):
    users: UserStats
    messages_sent: int = 0
    messages_today: int = 0
    announcements: int = 0
    groups: int = 0
    activity: List[ActivityStat] = Field(default_factory=list)
    top_senders: List[TopSenderStat] = Field(default_factory=list)

