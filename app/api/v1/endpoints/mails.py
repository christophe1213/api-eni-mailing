import os
from typing import Any, Optional
from fastapi import (
    APIRouter,
    Depends,
    Query,
    UploadFile,
    File,
    status,
    HTTPException,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.models.mail import PieceJointe
from app.schemas.mail import (
    MailSummary,
    MailDetail,
    ComposePayload,
    MailPatchPayload,
    BulkActionPayload,
    FolderCounts,
    AttachmentResponse,
)
from app.schemas.base import Page
from app.services.mail_service import mail_service

router = APIRouter()


@router.get("/counts", response_model=FolderCounts)
def get_folder_counts(
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.get_counts(db, user_id=current_user.id)


@router.get("", response_model=Page[MailSummary])
def get_mails(
    folder: str = Query("inbox"),
    q: Optional[str] = Query(None),
    unread: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.list_mails(
        db,
        user_id=current_user.id,
        folder=folder,
        q=q,
        unread=unread,
        page=page,
        page_size=pageSize,
    )


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    pj = db.get(PieceJointe, attachment_id)
    if not pj or not os.path.exists(pj.chemin_stockage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pièce jointe non trouvée.",
        )
    return FileResponse(
        path=pj.chemin_stockage,
        filename=pj.nom_fichier,
        media_type=pj.type_mime,
    )


@router.post("/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return await mail_service.save_attachment(db, file=file)


@router.get("/{mail_id}", response_model=MailDetail)
def get_mail_detail(
    mail_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.get_mail(db, user_id=current_user.id, message_id=mail_id)


@router.post("", response_model=MailDetail, status_code=status.HTTP_201_CREATED)
def send_or_draft_mail(
    payload: ComposePayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.send_mail(db, current_user=current_user, payload=payload)


@router.put("/{mail_id}", response_model=MailDetail)
def update_draft_mail(
    mail_id: int,
    payload: ComposePayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.send_mail(
        db, current_user=current_user, payload=payload, draft_id=mail_id
    )


@router.patch("/{mail_id}", response_model=MailSummary)
def patch_mail_status(
    mail_id: int,
    patch: MailPatchPayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return mail_service.patch_mail(
        db, user_id=current_user.id, message_id=mail_id, patch=patch
    )


@router.post("/bulk", status_code=status.HTTP_204_NO_CONTENT)
def bulk_mail_action(
    payload: BulkActionPayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> None:
    mail_service.bulk_action(db, user_id=current_user.id, payload=payload)
    return None


@router.delete("/{mail_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mail(
    mail_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> None:
    mail_service.delete_mail(db, user_id=current_user.id, message_id=mail_id)
    return None
