from typing import Optional, List, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import Utilisateur
from app.repositories.user_repository import user_repository
from app.schemas.user import (
    UserResponse,
    UserSummary,
    UserUpdate,
    UserPayload,
)
from app.schemas.base import Page
from app.core.security import get_password_hash
from app.services.avatar_service import avatar_url


def user_to_response(user: Utilisateur) -> UserResponse:
    return UserResponse(
        id=user.id,
        matricule=user.matricule,
        first_name=user.prenom,
        last_name=user.nom,
        email=user.email,
        role=user.role,  # type: ignore
        level=user.niveau_code,
        track=user.parcours_code,
        position=user.fonction,
        phone=user.telephone,
        signature=user.signature,
        notif_email=user.notif_email,
        avatar_url=avatar_url(user),
        active=user.actif,
        pending=user.en_attente,
        is_verified=getattr(user, "is_verified", True),
        created_at=user.date_creation,
        last_login_at=user.derniere_connexion,
    )


def user_to_summary(user: Utilisateur) -> UserSummary:
    return UserSummary(
        id=user.id,
        first_name=user.prenom,
        last_name=user.nom,
        email=user.email,
        role=user.role,  # type: ignore
        avatar_url=avatar_url(user),
    )


class UserService:
    def get_by_id(self, db: Session, user_id: int) -> Optional[UserResponse]:
        user = user_repository.get(db, id=user_id)
        if not user:
            return None
        return user_to_response(user)

    def get_user_model(self, db: Session, user_id: int) -> Optional[Utilisateur]:
        return user_repository.get(db, id=user_id)

    def get_by_email(self, db: Session, email: str) -> Optional[Utilisateur]:
        return user_repository.get_by_email(db, email=email)

    def get_by_matricule(self, db: Session, matricule: str) -> Optional[Utilisateur]:
        return user_repository.get_by_matricule(db, matricule=matricule)

    def list_users(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        role: Optional[str] = None,
        level: Optional[str] = None,
        track: Optional[str] = None,
        active: Optional[Union[bool, str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[UserResponse]:
        # active : "true" / "false" / "pending" (inscriptions à valider) / vide
        active_bool: Optional[bool] = None
        pending = active == "pending"
        if active is not None and active != "" and not pending:
            if isinstance(active, str):
                active_bool = active.lower() in ("true", "1")
            else:
                active_bool = bool(active)

        skip = (page - 1) * page_size
        users, total = user_repository.get_users_filtered(
            db,
            q=q,
            role=role,
            level=level,
            track=track,
            active=active_bool,
            pending=pending,
            skip=skip,
            limit=page_size,
        )

        return Page[UserResponse](
            items=[user_to_response(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_user(self, db: Session, *, payload: UserPayload) -> UserResponse:
        existing = user_repository.get_by_email(db, email=payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur avec cet email existe déjà.",
            )

        existing_mat = user_repository.get_by_matricule(db, matricule=payload.matricule)
        if existing_mat:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur avec ce matricule existe déjà.",
            )

        # Mot de passe par défaut pour création administrative
        default_pwd = get_password_hash("Eni@2026")

        user = Utilisateur(
            matricule=payload.matricule,
            nom=payload.last_name,
            prenom=payload.first_name,
            email=payload.email,
            mot_de_passe=default_pwd,
            role=payload.role,
            niveau_code=payload.level,
            parcours_code=payload.track,
            fonction=payload.position,
            telephone=payload.phone,
            actif=payload.active,
            is_verified=True,
            en_attente=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_response(user)

    def update_user(
        self, db: Session, *, user_id: int, payload: UserPayload
    ) -> UserResponse:
        user = user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé.",
            )

        user.matricule = payload.matricule
        user.prenom = payload.first_name
        user.nom = payload.last_name
        user.email = payload.email
        user.role = payload.role
        user.niveau_code = payload.level
        user.parcours_code = payload.track
        user.fonction = payload.position
        user.telephone = payload.phone
        user.actif = payload.active

        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_response(user)

    def set_active(self, db: Session, *, user_id: int, active: bool) -> UserResponse:
        user = user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé.",
            )
        user.actif = active
        # Valider ou refuser une inscription la sort de l'état « en attente »
        user.en_attente = False
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_response(user)

    def reset_password(self, db: Session, *, user_id: int) -> None:
        user = user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé.",
            )
        user.mot_de_passe = get_password_hash("Eni@2026")
        db.add(user)
        db.commit()

    def update_profile(
        self, db: Session, *, user: Utilisateur, payload: UserUpdate
    ) -> UserResponse:
        if payload.first_name is not None:
            user.prenom = payload.first_name
        if payload.last_name is not None:
            user.nom = payload.last_name
        if payload.phone is not None:
            user.telephone = payload.phone
        if payload.signature is not None:
            user.signature = payload.signature
        if payload.notif_email is not None:
            user.notif_email = payload.notif_email
        if payload.position is not None:
            user.fonction = payload.position
        if payload.active is not None:
            user.actif = payload.active

        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_response(user)


user_service = UserService()
