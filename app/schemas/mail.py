from datetime import datetime
from typing import Optional, List, Literal
from pydantic import Field
from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary

PriorityType = Literal["NORMALE", "HAUTE"]
FolderType = Literal["inbox", "starred", "sent", "drafts", "archive", "trash"]
RecipientType = Literal["TO", "CC", "BCC"]
BulkActionType = Literal["read", "unread", "archive", "trash", "delete", "restore"]


class AttachmentResponse(BaseSchema):
    id: int
    file_name: str
    mime_type: str
    size: int
    url: Optional[str] = None


class RecipientResponse(BaseSchema):
    user: UserSummary
    type: RecipientType


class GroupTargetResponse(BaseSchema):
    id: int
    name: str
    type: RecipientType


class MailSummary(BaseSchema):
    id: int
    subject: str
    preview: str = ""
    from_user: UserSummary = Field(..., serialization_alias="from", validation_alias="from")
    to: List[UserSummary] = Field(default_factory=list)
    date: datetime
    read: bool = False
    starred: bool = False
    folder: FolderType = "inbox"
    priority: PriorityType = "NORMALE"
    is_announcement: bool = False
    has_attachments: bool = False


class MailDetail(MailSummary):
    body: str = ""
    recipients: List[RecipientResponse] = Field(default_factory=list)
    groups: List[GroupTargetResponse] = Field(default_factory=list)
    attachments: List[AttachmentResponse] = Field(default_factory=list)
    parent_id: Optional[int] = None


class ComposePayload(BaseSchema):
    subject: str = ""
    body: str = ""
    priority: PriorityType = "NORMALE"
    to: List[int] = Field(default_factory=list)
    cc: List[int] = Field(default_factory=list)
    bcc: List[int] = Field(default_factory=list)
    group_ids: List[int] = Field(default_factory=list)
    attachment_ids: List[int] = Field(default_factory=list)
    parent_id: Optional[int] = None
    is_announcement: bool = False
    draft: bool = False


class MailPatchPayload(BaseSchema):
    read: Optional[bool] = None
    starred: Optional[bool] = None
    folder: Optional[FolderType] = None


class BulkActionPayload(BaseSchema):
    ids: List[int]
    action: BulkActionType


class FolderCounts(BaseSchema):
    inbox: int = 0
    starred: int = 0
    sent: int = 0
    drafts: int = 0
    archive: int = 0
    trash: int = 0
