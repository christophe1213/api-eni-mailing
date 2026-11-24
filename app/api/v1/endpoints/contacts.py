from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.schemas.base import Page
from app.schemas.contact import ContactPayload
from app.schemas.user import UserResponse
from app.services.audit_service import audit_service
from app.services.contact_service import contact_service

# Monté avec le préfixe "/users" : /users/{user_id}/contacts
router = APIRouter()


def _own_book(user_id: int, current_user: Utilisateur) -> None:
    """Un utilisateur n'accède qu'à son propre carnet, quel que soit son rôle.
    404 (et non 403) pour ne pas révéler l'existence du carnet d'un autre."""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ressource non trouvée."
        )


@router.get("/{user_id}/contacts", response_model=Page[UserResponse])
def get_contacts(
    user_id: int,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    _own_book(user_id, current_user)
    return contact_service.list_contacts(
        db, user=current_user, q=q, page=page, page_size=pageSize
    )


@router.post(
    "/{user_id}/contacts",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_contact(
    user_id: int,
    payload: ContactPayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    _own_book(user_id, current_user)
    contact = contact_service.add_contact(
        db, user=current_user, contact_user_id=payload.contact_user_id
    )
    audit_service.log(
        db,
        user_id=current_user.id,
        action="CONTACT_ADD",
        details={"contactUserId": payload.contact_user_id},
    )
    return contact


@router.delete(
    "/{user_id}/contacts/{contact_user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_contact(
    user_id: int,
    contact_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> None:
    _own_book(user_id, current_user)
    contact_service.remove_contact(
        db, user=current_user, contact_user_id=contact_user_id
    )
    audit_service.log(
        db,
        user_id=current_user.id,
        action="CONTACT_REMOVE",
        details={"contactUserId": contact_user_id},
    )
    return None


@router.get("/{user_id}/contacts/{contact_user_id}/exists")
def contact_exists(
    user_id: int,
    contact_user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    _own_book(user_id, current_user)
    exists = contact_service.exists_contact(
        db, user_id=current_user.id, contact_user_id=contact_user_id
    )
    return {"exists": exists}
