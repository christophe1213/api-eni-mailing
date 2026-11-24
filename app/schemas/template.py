from datetime import datetime
from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary


class TemplatePayload(BaseSchema):
    title: str
    category: str
    subject: str
    body: str


class TemplateResponse(BaseSchema):
    id: int
    title: str
    category: str
    subject: str
    body: str
    author: UserSummary
    updated_at: datetime

