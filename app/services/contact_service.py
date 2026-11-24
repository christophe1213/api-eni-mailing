from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.user import Utilisateur
from app.repositories.contact_repository import contact_repository
from app.schemas.base import Page
from app.schemas.user import UserResponse
from app.services.user_service import user_to_response


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ContactService:
    def list_contacts(
        self,
        db: Session,
        *,
        user: Utilisateur,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[UserResponse]:
        skip = (page - 1) * page_size
        contacts, total = contact_repository.list_for_user(
            db, user_id=user.id, q=q, skip=skip, limit=page_size
        )
        return Page[UserResponse](
            items=[user_to_response(contact.contact_utilisateur) for contact in contacts],
            total=total,
            page=page,
            page_size=page_size,
        )

    def add_contact(
        self, db: Session, *, user: Utilisateur, contact_user_id: int
    ) -> UserResponse:
        if contact_user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas vous ajouter vous-même en contact.",
            )
        target = db.get(Utilisateur, contact_user_id)
        if not target or not target.actif:
            raise _not_found("Utilisateur non trouvé.")

        duplicate = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet utilisateur est déjà dans vos contacts.",
        )
        if contact_repository.get_by_target(
            db, user_id=user.id, contact_user_id=contact_user_id
        ):
            raise duplicate
        try:
            created = contact_repository.create(
                db, user_id=user.id, contact_user_id=contact_user_id
            )
        except IntegrityError:
            db.rollback()
            raise duplicate
        return user_to_response(created.contact_utilisateur)

    def remove_contact(
        self, db: Session, *, user: Utilisateur, contact_user_id: int
    ) -> None:
        contact = contact_repository.get_by_target(
            db, user_id=user.id, contact_user_id=contact_user_id
        )
        if not contact:
            raise _not_found("Contact non trouvé.")
        contact_repository.delete(db, contact=contact)

    def exists_contact(
        self, db: Session, *, user_id: int, contact_user_id: int
    ) -> bool:
        return (
            contact_repository.get_by_target(
                db, user_id=user_id, contact_user_id=contact_user_id
            )
            is not None
        )


contact_service = ContactService()
