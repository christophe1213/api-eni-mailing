from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import Utilisateur
from app.repositories.user_repository import user_repository
from app.schemas.auth import LoginPayload, Token
from app.schemas.user import RegisterPayload, UserResponse
from app.services.user_service import user_to_response
from app.core.security import verify_password, get_password_hash, create_access_token


class AuthService:
    def authenticate(
        self, db: Session, *, login_data: LoginPayload
    ) -> Optional[Tuple[str, UserResponse]]:
        user = user_repository.get_by_email(db, email=login_data.email)
        if not user:
            return None
        if not verify_password(login_data.password, user.mot_de_passe):
            return None
        if not getattr(user, "is_verified", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Votre adresse e-mail n'a pas encore été vérifiée par code OTP.",
            )
        if user.en_attente:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Votre demande d'inscription est en cours de vérification par l'administration.",
            )
        if not user.actif:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce compte est désactivé. Contactez l'administrateur (RG11).",
            )

        # Mise à jour de la dernière connexion
        user.derniere_connexion = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(subject=str(user.id))
        return token, user_to_response(user)

    def register(
        self, db: Session, *, payload: RegisterPayload
    ) -> Utilisateur:
        # Création du compte utilisateur (inactif par défaut si en attente de validation)
        new_user = Utilisateur(
            matricule=payload.matricule,
            nom=payload.last_name,
            prenom=payload.first_name,
            email=payload.email,
            email_verification=payload.email_verification.strip().lower(),
            email_verification_verifie=False,
            mot_de_passe=get_password_hash(payload.password),
            role=payload.role,
            niveau_code=payload.level,
            parcours_code=payload.track,
            fonction=payload.position or payload.department,
            telephone=payload.phone,
            notif_email=True,
            is_verified=False,  # En attente de validation OTP de l'e-mail
            actif=False,  # En attente de validation administrative
            en_attente=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user


auth_service = AuthService()

