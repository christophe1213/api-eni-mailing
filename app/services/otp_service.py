import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.otp import OtpCode
from app.models.user import Utilisateur


def _utcnow() -> datetime:
    """Heure UTC *naïve* (sans tzinfo), à utiliser pour toutes les dates de la table otp_code.

    Les colonnes created_at / expires_at sont des « timestamp without time zone ». Si on leur envoie un datetime
    « aware », PostgreSQL le convertit dans le fuseau de la SESSION (ex. UTC+3 à Madagascar) avant de l'enregistrer
    sans fuseau ; relu comme de l'UTC, il apparaît décalé de plusieurs heures : le délai de renvoi de 60 s dure alors
    des heures (429) et un code reste valable des heures. Écrire de l'UTC naïf rend le résultat indépendant du
    fuseau du serveur PostgreSQL.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive_utc(value: datetime) -> datetime:
    """Ramène une date relue en base à de l'UTC naïf (au cas où la colonne deviendrait un timestamptz)."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class OtpService:
    @staticmethod
    def generate_code() -> str:
        """Génère un code OTP aléatoire de 6 chiffres cryptographiquement sûr."""
        return "".join(secrets.choice("0123456789") for _ in range(6))

    @staticmethod
    def hash_code(code: str, user_id: int) -> str:
        """
        Hache le code OTP avec SHA-256 combiné à la SECRET_KEY et au user_id
        comme sel/poivre applicatif. Ne jamais stocker le code en clair.
        """
        payload = f"{code}:{settings.SECRET_KEY}:{user_id}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def verify_hash(self, code: str, user_id: int, stored_hash: str) -> bool:
        """Comparaison en temps constant pour prévenir les attaques temporelles."""
        computed = self.hash_code(code, user_id)
        return secrets.compare_digest(computed, stored_hash)

    def create_otp(
        self, db: Session, *, user_id: int, purpose: str = "REGISTER"
    ) -> str:
        """
        Crée un nouvel OTP en vérifiant le délai de renvoi (cooldown de 60s)
        et en invalidant les anciens codes encore actifs pour cet objectif.
        """
        now = _utcnow()

        # 1. Vérifier le cooldown de renvoi (protection contre le spam)
        last_otp = db.scalars(
            select(OtpCode)
            .where(OtpCode.user_id == user_id, OtpCode.purpose == purpose)
            .order_by(OtpCode.created_at.desc())
        ).first()

        if last_otp and last_otp.created_at:
            created_at = _as_naive_utc(last_otp.created_at)
            elapsed = (now - created_at).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Veuillez patienter {remaining} secondes avant de demander un nouveau code.",
                )

        # 2. Invalider les anciens codes non utilisés pour cet utilisateur et cet objectif
        db.execute(
            update(OtpCode)
            .where(
                OtpCode.user_id == user_id,
                OtpCode.purpose == purpose,
                OtpCode.is_used == False,  # noqa: E712
            )
            .values(is_used=True)
        )

        # 3. Génération et stockage du nouvel OTP
        code = self.generate_code()
        code_hash = self.hash_code(code, user_id)
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_record = OtpCode(
            user_id=user_id,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False,
            attempts=0,
            created_at=now,
        )
        db.add(otp_record)
        db.commit()

        # Le code en clair n'est retourné qu'au service appelant pour l'e-mail
        return code

    def verify_otp(
        self, db: Session, *, user_id: int, code: str, purpose: str = "REGISTER"
    ) -> bool:
        """
        Vérifie la validité du code OTP (expiration, tentatives max, correspondance).
        """
        now = _utcnow()

        # Rechercher le dernier OTP actif pour ce user et cet objectif
        otp_record = db.scalars(
            select(OtpCode)
            .where(
                OtpCode.user_id == user_id,
                OtpCode.purpose == purpose,
                OtpCode.is_used == False,  # noqa: E712
            )
            .order_by(OtpCode.created_at.desc())
        ).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun code de vérification valide trouvé. Veuillez demander un nouveau code.",
            )

        # Vérifier l'expiration
        expires_at = _as_naive_utc(otp_record.expires_at)

        if now > expires_at:
            otp_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le code de vérification a expiré. Veuillez demander un nouveau code.",
            )

        # Vérifier le nombre de tentatives déjà effectuées
        if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
            otp_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nombre maximal de tentatives dépassé pour ce code. Veuillez demander un nouveau code.",
            )

        # Vérifier la validité du code
        if not self.verify_hash(code, user_id, otp_record.code_hash):
            otp_record.attempts += 1
            remaining = settings.OTP_MAX_ATTEMPTS - otp_record.attempts
            if remaining <= 0:
                otp_record.is_used = True
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Code incorrect. Nombre maximal de tentatives atteint, le code a été invalidé.",
                )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code de vérification incorrect. Tentatives restantes : {remaining}.",
            )

        # Succès : marquer le code comme consommé
        otp_record.is_used = True
        db.commit()
        return True

    def create_reset_token(self, *, user_id: int, email: str) -> str:
        """Génère un jeton temporaire JWT (valable 15 min) après validation OTP pour mot de passe oublié."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=15)
        payload = {
            "sub": str(user_id),
            "email": email.lower(),
            "purpose": "password_reset",
            "exp": expire,
            "iat": now,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_reset_token(self, *, token: str, email: str) -> int:
        """Valide le jeton temporaire de réinitialisation de mot de passe."""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("purpose") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Jeton de réinitialisation invalide.",
                )
            if payload.get("email") != email.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="L'adresse e-mail ne correspond pas au jeton de réinitialisation.",
                )
            user_id = int(payload.get("sub", 0))
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Jeton de réinitialisation invalide.",
                )
            return user_id
        except (JWTError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le jeton de réinitialisation est invalide ou a expiré.",
            )


otp_service = OtpService()

