from datetime import datetime
from typing import Optional, List, Literal
from pydantic import Field
from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary, RoleType, LevelType, TrackType

GroupType = Literal["AUTO", "MANUELLE"]


class GroupPayload(BaseSchema):
    name: str
    address: str
    description: Optional[str] = ""
    type: GroupType
    criteria_role: Optional[RoleType] = None
    criteria_level: Optional[LevelType] = None
    criteria_track: Optional[TrackType] = None
    open_to_students: bool = False
    member_ids: List[int] = Field(default_factory=list)


class GroupResponse(BaseSchema):
    id: int
    name: str
    address: str
    description: Optional[str] = ""
    type: GroupType
    criteria_role: Optional[RoleType] = None
    criteria_level: Optional[LevelType] = None
    criteria_track: Optional[TrackType] = None
    open_to_students: bool = False
    owner: UserSummary
    member_count: int = 0
    created_at: datetime
    members: Optional[List[UserSummary]] = None

