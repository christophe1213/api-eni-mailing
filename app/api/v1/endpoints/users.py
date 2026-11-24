import os
from typing import Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.schemas.user import UserResponse, UserPayload, UserStatusUpdate
from app.schemas.base import Page
from app.services.user_service import user_service
from app.services.audit_service import audit_service
from app.services.avatar_service import avatar_path

router = APIRouter()


@router.get("", response_model=Page[UserResponse])
def get_users(
    db: Session = Depends(deps.get_db),
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    track: Optional[str] = Query(None),
    active: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=1000),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return user_service.list_users(
        db,
        q=q,
        role=role,
        level=level,
        track=track,
        active=active,
        page=page,
        page_size=pageSize,
    )


@router.get("/{user_id}/avatar")
def get_user_avatar(user_id: int, db: Session = Depends(deps.get_db)) -> Any:
    """Photo de profil. Volontairement sans authentification : une balise <img> ne peut pas
    envoyer l'en-tête Authorization. L'URL est versionnée (?v=) donc cachable longtemps."""
    user = db.get(Utilisateur, user_id)
    path = avatar_path(user_id)
    if not user or not user.photo_maj or not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photo de profil introuvable."
        )
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    user = user_service.get_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé."
        )
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserPayload,
    db: Session = Depends(deps.get_db),
    admin_user: Utilisateur = Depends(deps.get_current_admin),
) -> Any:
    created = user_service.create_user(db, payload=payload)
    audit_service.log(
        db,
        user_id=admin_user.id,
        action="USER_CREATE",
        details={"createdUserId": created.id, "email": created.email},
    )
    return created


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserPayload,
    db: Session = Depends(deps.get_db),
    admin_user: Utilisateur = Depends(deps.get_current_admin),
) -> Any:
    updated = user_service.update_user(db, user_id=user_id, payload=payload)
    audit_service.log(
        db,
        user_id=admin_user.id,
        action="USER_UPDATE",
        details={"updatedUserId": updated.id, "email": updated.email},
    )
    return updated


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_user_active_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(deps.get_db),
    admin_user: Utilisateur = Depends(deps.get_current_admin),
) -> Any:
    updated = user_service.set_active(db, user_id=user_id, active=payload.active)
    audit_service.log(
        db,
        user_id=admin_user.id,
        action="USER_ENABLE" if payload.active else "USER_DISABLE",
        details={"userId": user_id, "active": payload.active},
    )
    return updated


