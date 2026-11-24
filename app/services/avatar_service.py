import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import Utilisateur

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def avatar_path(user_id: int) -> str:
    return os.path.join(settings.AVATAR_DIR, f"{user_id}.jpg")


def avatar_url(user: Utilisateur) -> Optional[str]:
    """URL publique (versionnée) de la photo, ou None si l'utilisateur n'en a pas."""
    if not user.photo_maj:
        return None
    version = int(user.photo_maj.replace(tzinfo=timezone.utc).timestamp())
    return f"{settings.API_V1_STR}/users/{user.id}/avatar?v={version}"


class AvatarService:
    async def save(self, db: Session, *, user: Utilisateur, file: UploadFile) -> Utilisateur:
        # On lit au plus MAX+1 octets : inutile de charger un fichier énorme en mémoire
        data = await file.read(settings.MAX_AVATAR_SIZE + 1)
        if len(data) > settings.MAX_AVATAR_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Image trop volumineuse (5 Mo maximum).",
            )

        invalid = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Format non pris en charge (JPEG, PNG ou WebP).",
        )
        try:
            # Le format est déterminé par le contenu réel, pas par l'extension ni le Content-Type
            probe = Image.open(io.BytesIO(data))
            if probe.format not in ALLOWED_FORMATS:
                raise invalid
            probe.verify()
            img = Image.open(io.BytesIO(data))
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")
            size = settings.AVATAR_PIXELS
            # Recadrage carré au centre + redimensionnement ; ré-encodage = suppression des métadonnées EXIF
            img = ImageOps.fit(img, (size, size), Image.LANCZOS)
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise invalid

        os.makedirs(settings.AVATAR_DIR, exist_ok=True)
        final_path = avatar_path(user.id)
        tmp_path = f"{final_path}.tmp"
        img.save(tmp_path, "JPEG", quality=85, optimize=True)
        os.replace(tmp_path, final_path)  # écriture atomique

        user.photo_maj = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def delete(self, db: Session, *, user: Utilisateur) -> Utilisateur:
        path = avatar_path(user.id)
        if os.path.exists(path):
            os.remove(path)
        user.photo_maj = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


avatar_service = AvatarService()
