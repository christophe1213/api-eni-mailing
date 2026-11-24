import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Set
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.realtime import manager
from app.models.mail import Boite, Message
from app.models.user import Utilisateur
from app.repositories.mail_repository import mail_repository
from app.repositories.group_repository import group_repository
from app.repositories.user_repository import user_repository
from app.services.audit_service import audit_service
from app.schemas.mail import (
    MailSummary,
    MailDetail,
    ComposePayload,
    MailPatchPayload,
    BulkActionPayload,
    FolderCounts,
    AttachmentResponse,
    RecipientResponse,
    GroupTargetResponse,
)
from app.schemas.user import UserSummary
from app.services.avatar_service import avatar_url
from app.schemas.base import Page


def user_to_summary(u: Utilisateur) -> UserSummary:
    return UserSummary(
        id=u.id,
        first_name=u.prenom,
        last_name=u.nom,
        email=u.email,
        role=u.role,  # type: ignore
        avatar_url=avatar_url(u),
    )


def box_to_summary(box: Boite) -> MailSummary:
    msg = box.message
    # Destinataires principaux (TO)
    to_users = [
        user_to_summary(b.utilisateur)
        for b in msg.boites
        if b.type_dest == "TO"
    ]

    # Snippet / preview
    preview = msg.corps[:140].replace("\n", " ").strip() if msg.corps else ""

    return MailSummary(
        id=msg.id,
        subject=msg.objet,
        preview=preview,
        from_user=user_to_summary(msg.expediteur),
        to=to_users,
        date=msg.date_envoi or msg.date_creation,
        read=box.lu,
        starred=box.favori,
        folder=box.dossier.lower(),  # type: ignore
        priority=msg.priorite,  # type: ignore
        is_announcement=msg.est_annonce,
        has_attachments=bool(msg.pieces_jointes),
    )


def box_to_detail(box: Boite, current_user_id: int) -> MailDetail:
    msg = box.message
    summary = box_to_summary(box)

    # Récupérer les destinataires selon RG06 (Cci visible uniquement par l'expéditeur ou soi-même)
    recipients: List[RecipientResponse] = []
    is_sender = (msg.expediteur_id == current_user_id)

    for b in msg.boites:
        if b.type_dest == "FROM":
            continue
        if b.type_dest == "BCC" and not is_sender and b.utilisateur_id != current_user_id:
            # Ne pas divulguer les autres destinataires BCC
            continue
        recipients.append(
            RecipientResponse(
                user=user_to_summary(b.utilisateur),
                type=b.type_dest,  # type: ignore
            )
        )

    # Groupes cibles
    groups: List[GroupTargetResponse] = [
        GroupTargetResponse(
            id=ml.liste_id,
            name=ml.liste.nom if ml.liste else f"Groupe #{ml.liste_id}",
            type=ml.type_dest,  # type: ignore
        )
        for ml in msg.groupes_cibles
    ]

    # Pièces jointes
    attachments: List[AttachmentResponse] = [
        AttachmentResponse(
            id=pj.id,
            file_name=pj.nom_fichier,
            mime_type=pj.type_mime,
            size=pj.taille,
            url=f"/api/mails/attachments/{pj.id}",
        )
        for pj in msg.pieces_jointes
    ]

    return MailDetail(
        **summary.model_dump(by_alias=False),
        body=msg.corps,
        recipients=recipients,
        groups=groups,
        attachments=attachments,
        parent_id=msg.parent_id,
    )


class MailService:
    def get_counts(self, db: Session, user_id: int) -> FolderCounts:
        raw_counts = mail_repository.get_folder_counts(db, user_id=user_id)
        return FolderCounts(**raw_counts)

    def list_mails(
        self,
        db: Session,
        user_id: int,
        folder: str,
        q: Optional[str] = None,
        unread: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[MailSummary]:
        skip = (page - 1) * page_size
        boxes, total = mail_repository.get_mails_by_folder(
            db,
            user_id=user_id,
            folder=folder,
            q=q,
            unread=unread,
            skip=skip,
            limit=page_size,
        )

        items = [box_to_summary(b) for b in boxes]
        return Page[MailSummary](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_mail(
        self, db: Session, user_id: int, message_id: int
    ) -> MailDetail:
        box = mail_repository.get_mail_box(db, user_id=user_id, message_id=message_id)
        if not box:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé.",
            )

        # Si non lu dans INBOX, marquer comme lu (comportement standard messagerie)
        if not box.lu and box.dossier == "INBOX":
            box.lu = True
            box.date_lecture = datetime.now(timezone.utc)
            db.add(box)
            db.commit()
            db.refresh(box)
            manager.notify([user_id], {"type": "counts.changed"})

        return box_to_detail(box, current_user_id=user_id)

    def send_mail(
        self,
        db: Session,
        *,
        current_user: Utilisateur,
        payload: ComposePayload,
        draft_id: Optional[int] = None,
    ) -> MailDetail:
        # Vérification RG08 : Un étudiant ne peut écrire à une liste que si elle est marquée ouverte_etudiants
        target_groups = []
        if payload.group_ids:
            for gid in payload.group_ids:
                g = group_repository.get_by_id(db, gid)
                if not g:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"La liste de diffusion #{gid} n'existe pas.",
                    )
                if current_user.role == "ETUDIANT" and not g.ouverte_etudiants:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Les étudiants ne sont pas autorisés à écrire à la liste '{g.nom}'.",
                    )
                target_groups.append(g)

        # Si ce n'est pas un brouillon, vérifier qu'il y a des destinataires et un objet
        if not payload.draft:
            if not payload.to and not payload.cc and not payload.bcc and not payload.group_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Veuillez spécifier au moins un destinataire ou une liste.",
                )

        # Récupération ou création du message
        if draft_id:
            msg = mail_repository.get_message(db, draft_id)
            if not msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Brouillon introuvable."
                )
            if msg.expediteur_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé."
                )
            if msg.date_envoi is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Un message déjà envoyé ne peut plus être modifié.",
                )
            msg = mail_repository.update_draft(db, message=msg, payload=payload)
        else:
            msg = mail_repository.create_message(
                db,
                expediteur_id=current_user.id,
                objet=payload.subject,
                corps=payload.body,
                priorite=payload.priority,
                est_annonce=payload.is_announcement,
                parent_id=payload.parent_id,
                is_draft=payload.draft,
            )

        # Attacher les pièces jointes
        if payload.attachment_ids:
            mail_repository.attach_files_to_message(db, payload.attachment_ids, msg.id)

        # Supprimer les anciennes associations pour mise à jour de brouillon
        if draft_id:
            for ml in msg.groupes_cibles:
                db.delete(ml)
            for b in msg.boites:
                db.delete(b)
            db.flush()

        # Enregistrer les groupes cibles
        for g in target_groups:
            mail_repository.add_message_group(
                db, message_id=msg.id, liste_id=g.id, type_dest="TO"
            )

        # Résolution des destinataires
        to_uids: Set[int] = set(payload.to)
        cc_uids: Set[int] = set(payload.cc)
        bcc_uids: Set[int] = set(payload.bcc)

        # Étendre les membres des groupes
        for g in target_groups:
            members = group_repository.resolve_members(db, g)
            for m in members:
                # Éviter d'ajouter l'expéditeur comme destinataire de son propre message
                if m.id != current_user.id:
                    to_uids.add(m.id)

        # S'assurer de l'unicité et de l'exclusion de l'expéditeur
        cc_uids = cc_uids - to_uids
        bcc_uids = bcc_uids - to_uids - cc_uids
        to_uids.discard(current_user.id)
        cc_uids.discard(current_user.id)
        bcc_uids.discard(current_user.id)

        if payload.draft:
            # Boîte de l'expéditeur : DRAFTS
            sender_box = mail_repository.create_box(
                db,
                message_id=msg.id,
                utilisateur_id=current_user.id,
                type_dest="FROM",
                dossier="DRAFTS",
                lu=True,
            )
        else:
            # Boîte de l'expéditeur : SENT
            sender_box = mail_repository.create_box(
                db,
                message_id=msg.id,
                utilisateur_id=current_user.id,
                type_dest="FROM",
                dossier="SENT",
                lu=True,
            )

            # Boîtes des destinataires
            for uid in to_uids:
                mail_repository.create_box(
                    db,
                    message_id=msg.id,
                    utilisateur_id=uid,
                    type_dest="TO",
                    dossier="INBOX",
                    lu=False,
                )
            for uid in cc_uids:
                mail_repository.create_box(
                    db,
                    message_id=msg.id,
                    utilisateur_id=uid,
                    type_dest="CC",
                    dossier="INBOX",
                    lu=False,
                )
            for uid in bcc_uids:
                mail_repository.create_box(
                    db,
                    message_id=msg.id,
                    utilisateur_id=uid,
                    type_dest="BCC",
                    dossier="INBOX",
                    lu=False,
                )

            # RG10 : Audit si diffusion vers > 50 membres ou annonce
            total_recipients_count = len(to_uids) + len(cc_uids) + len(bcc_uids)
            if total_recipients_count > 50 or payload.is_announcement:
                audit_service.log(
                    db,
                    user_id=current_user.id,
                    action="BROADCAST" if total_recipients_count > 50 else "ANNOUNCEMENT",
                    details={
                        "messageId": msg.id,
                        "subject": msg.objet,
                        "recipientCount": total_recipients_count,
                    },
                )

        db.commit()
        db.refresh(sender_box)

        # Temps réel : toujours APRÈS le commit, sinon le client peut refetch avant que la donnée existe.
        manager.notify([current_user.id], {"type": "counts.changed"})
        if not payload.draft:
            manager.notify(
                to_uids | cc_uids | bcc_uids,
                {
                    "type": "mail.new",
                    "mailId": msg.id,
                    "from": f"{current_user.prenom} {current_user.nom}",
                    "subject": msg.objet,
                },
            )
        return box_to_detail(sender_box, current_user_id=current_user.id)

    def patch_mail(
        self,
        db: Session,
        *,
        user_id: int,
        message_id: int,
        patch: MailPatchPayload,
    ) -> MailSummary:
        box = mail_repository.patch_box(
            db,
            user_id=user_id,
            message_id=message_id,
            read=patch.read,
            starred=patch.starred,
            folder=patch.folder,
        )
        if not box:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé.",
            )
        manager.notify([user_id], {"type": "counts.changed"})
        return box_to_summary(box)

    def delete_mail(self, db: Session, *, user_id: int, message_id: int) -> None:
        success = mail_repository.delete_mail(db, user_id=user_id, message_id=message_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé.",
            )
        manager.notify([user_id], {"type": "counts.changed"})

    def bulk_action(
        self,
        db: Session,
        *,
        user_id: int,
        payload: BulkActionPayload,
    ) -> None:
        mail_repository.bulk_action(
            db, user_id=user_id, ids=payload.ids, action=payload.action
        )
        manager.notify([user_id], {"type": "counts.changed"})

    async def save_attachment(
        self, db: Session, file: UploadFile
    ) -> AttachmentResponse:
        # RG09 : Vérification de l'extension
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext in settings.FORBIDDEN_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Les extensions de fichier {', '.join(settings.FORBIDDEN_EXTENSIONS)} sont interdites.",
            )

        content = await file.read()
        size = len(content)

        # RG09 : Taille max 10 Mo par fichier
        if size > settings.MAX_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le fichier dépasse la limite maximale de 10 Mo.",
            )

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        storage_path = os.path.join(settings.UPLOAD_DIR, unique_name)

        with open(storage_path, "wb") as f:
            f.write(content)

        pj = mail_repository.create_attachment(
            db,
            nom_fichier=file.filename or "fichier",
            type_mime=file.content_type or "application/octet-stream",
            taille=size,
            chemin_stockage=storage_path,
        )

        return AttachmentResponse(
            id=pj.id,
            file_name=pj.nom_fichier,
            mime_type=pj.type_mime,
            size=pj.taille,
            url=f"/api/mails/attachments/{pj.id}",
        )


mail_service = MailService()

