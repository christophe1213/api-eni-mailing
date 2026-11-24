from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary


class ContactPayload(BaseSchema):
    # Corps JSON : {"contactUserId": 12}
    contact_user_id: int


class ContactResponse(BaseSchema):
    """Format historique d'une relation contact, conservé pour les imports existants."""

    id: int
    user: UserSummary
