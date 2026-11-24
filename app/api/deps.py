from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import Utilisateur
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

ROLE_RANK = {
    "ETUDIANT": 1,
    "ENSEIGNANT": 2,
    "PERSONNEL": 3,
    "ADMIN": 4,
}


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> Utilisateur:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les identifiants.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(Utilisateur, int(token_data.sub)) if token_data.sub else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé."
        )
    return user


def get_current_active_user(
    current_user: Utilisateur = Depends(get_current_user),
) -> Utilisateur:
    if not current_user.actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Compte inactif ou non validé."
        )
    return current_user


def get_current_teacher_or_above(
    current_user: Utilisateur = Depends(get_current_active_user),
) -> Utilisateur:
    if ROLE_RANK.get(current_user.role, 0) < ROLE_RANK["ENSEIGNANT"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits d'enseignant ou supérieur requis.",
        )
    return current_user


def get_current_personnel_or_admin(
    current_user: Utilisateur = Depends(get_current_active_user),
) -> Utilisateur:
    if ROLE_RANK.get(current_user.role, 0) < ROLE_RANK["PERSONNEL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits de personnel ou administrateur requis.",
        )
    return current_user


def get_current_admin(
    current_user: Utilisateur = Depends(get_current_active_user),
) -> Utilisateur:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilèges d'administrateur requis.",
        )
    return current_user


def get_user_from_token(token: str) -> Utilisateur | None:
    """Authentification hors requête HTTP (WebSocket). Ouvre et referme sa propre session."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None
    if not token_data.sub:
        return None
    db = SessionLocal()
    try:
        user = db.get(Utilisateur, int(token_data.sub))
        if not user or not user.actif:
            return None
        db.expunge(user)  # on ne garde que l'id côté WebSocket
        return user
    finally:
        db.close()
