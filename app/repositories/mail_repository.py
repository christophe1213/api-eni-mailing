from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, joinedload
from app.models.mail import Message, Boite, MessageListe, PieceJointe
from app.models.user import Utilisateur
from app.models.group import ListeDiffusion
from app.schemas.mail import ComposePayload, BulkActionType


class MailRepository:
    def get_folder_counts(self, db: Session, user_id: int) -> dict:
        results = db.execute(
            select(Boite.dossier, func.count(Boite.id))
            .where(Boite.utilisateur_id == user_id)
            .group_by(Boite.dossier)
        ).all()

        folder_map = {dossier.lower(): cnt for dossier, cnt in results}

        # Pour inbox, compter les non lus
        unread_inbox = db.scalar(
            select(func.count(Boite.id)).where(
                Boite.utilisateur_id == user_id,
                Boite.dossier == "INBOX",
                Boite.lu == False,
            )
        ) or 0

        # Compte favoris
        starred_count = db.scalar(
            select(func.count(Boite.id)).where(
                Boite.utilisateur_id == user_id,
                Boite.favori == True,
                Boite.dossier != "TRASH",
            )
        ) or 0

        return {
            "inbox": unread_inbox,
            "starred": starred_count,
            "sent": folder_map.get("sent", 0),
            "drafts": folder_map.get("drafts", 0),
            "archive": folder_map.get("archive", 0),
            "trash": folder_map.get("trash", 0),
        }

    def get_mails_by_folder(
        self,
        db: Session,
        user_id: int,
        folder: str,
        q: Optional[str] = None,
        unread: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Boite], int]:
        query = (
            select(Boite)
            .join(Boite.message)
            .join(Message.expediteur)
            .options(
                joinedload(Boite.message).joinedload(Message.expediteur),
                joinedload(Boite.message).joinedload(Message.pieces_jointes),
                joinedload(Boite.message).joinedload(Message.boites).joinedload(Boite.utilisateur),
            )
            .where(Boite.utilisateur_id == user_id)
        )
        count_query = (
            select(func.count(Boite.id))
            .join(Boite.message)
            .join(Message.expediteur)
            .where(Boite.utilisateur_id == user_id)
        )

        folder_lower = folder.lower()
        if folder_lower == "starred":
            condition = and_(Boite.favori == True, Boite.dossier != "TRASH")
        else:
            condition = Boite.dossier == folder_lower.upper()

        query = query.where(condition)
        count_query = count_query.where(condition)

        if unread is True:
            query = query.where(Boite.lu == False)
            count_query = count_query.where(Boite.lu == False)

        if q:
            pattern = f"%{q.strip()}%"
            search_cond = or_(
                Message.objet.ilike(pattern),
                Message.corps.ilike(pattern),
                Utilisateur.nom.ilike(pattern),
                Utilisateur.prenom.ilike(pattern),
                Utilisateur.email.ilike(pattern),
            )
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)

        total = db.scalar(count_query) or 0
        boxes = list(
            db.scalars(
                query.order_by(Message.date_creation.desc())
                .offset(skip)
                .limit(limit)
            ).unique().all()
        )
        return boxes, total

    def get_mail_box(
        self, db: Session, user_id: int, message_id: int
    ) -> Optional[Boite]:
        stmt = (
            select(Boite)
            .where(Boite.utilisateur_id == user_id, Boite.message_id == message_id)
            .options(
                joinedload(Boite.message).joinedload(Message.expediteur),
                joinedload(Boite.message).joinedload(Message.pieces_jointes),
                joinedload(Boite.message).joinedload(Message.groupes_cibles).joinedload(MessageListe.liste),
                joinedload(Boite.message).joinedload(Message.boites).joinedload(Boite.utilisateur),
            )
        )
        return db.scalars(stmt).first()

    def get_message(self, db: Session, message_id: int) -> Optional[Message]:
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                joinedload(Message.expediteur),
                joinedload(Message.pieces_jointes),
                joinedload(Message.groupes_cibles).joinedload(MessageListe.liste),
                joinedload(Message.boites).joinedload(Boite.utilisateur),
            )
        )
        return db.scalars(stmt).first()

    def create_message(
        self,
        db: Session,
        *,
        expediteur_id: int,
        objet: str,
        corps: str,
        priorite: str = "NORMALE",
        est_annonce: bool = False,
        parent_id: Optional[int] = None,
        is_draft: bool = False,
    ) -> Message:
        msg = Message(
            expediteur_id=expediteur_id,
            objet=objet,
            corps=corps,
            priorite=priorite,
            est_annonce=est_annonce,
            parent_id=parent_id,
            date_envoi=None if is_draft else datetime.now(timezone.utc),
        )
        db.add(msg)
        db.flush()
        return msg

    def create_box(
        self,
        db: Session,
        *,
        message_id: int,
        utilisateur_id: int,
        type_dest: str,
        dossier: str,
        lu: bool = False,
        favori: bool = False,
    ) -> Boite:
        boite = Boite(
            message_id=message_id,
            utilisateur_id=utilisateur_id,
            type_dest=type_dest,
            dossier=dossier,
            lu=lu,
            favori=favori,
        )
        db.add(boite)
        return boite

    def add_message_group(
        self, db: Session, *, message_id: int, liste_id: int, type_dest: str
    ) -> MessageListe:
        ml = MessageListe(
            message_id=message_id,
            liste_id=liste_id,
            type_dest=type_dest,
        )
        db.add(ml)
        return ml

    def update_draft(
        self, db: Session, *, message: Message, payload: ComposePayload
    ) -> Message:
        message.objet = payload.subject
        message.corps = payload.body
        message.priorite = payload.priority
        message.est_annonce = payload.is_announcement
        message.parent_id = payload.parent_id
        if not payload.draft:
            message.date_envoi = datetime.now(timezone.utc)
        db.add(message)
        return message

    def patch_box(
        self,
        db: Session,
        *,
        user_id: int,
        message_id: int,
        read: Optional[bool] = None,
        starred: Optional[bool] = None,
        folder: Optional[str] = None,
    ) -> Optional[Boite]:
        boite = self.get_mail_box(db, user_id=user_id, message_id=message_id)
        if not boite:
            return None

        if read is not None:
            boite.lu = read
            boite.date_lecture = datetime.now(timezone.utc) if read else None
        if starred is not None:
            boite.favori = starred
        if folder is not None:
            folder_upper = folder.upper()
            if folder_upper in ["INBOX", "SENT", "DRAFTS", "ARCHIVE", "TRASH"]:
                boite.dossier = folder_upper
                if folder_upper == "TRASH":
                    boite.date_suppression = datetime.now(timezone.utc)
                else:
                    boite.date_suppression = None

        db.add(boite)
        db.commit()
        db.refresh(boite)
        return boite

    def delete_mail(self, db: Session, user_id: int, message_id: int) -> bool:
        boite = self.get_mail_box(db, user_id=user_id, message_id=message_id)
        if not boite:
            return False

        if boite.dossier == "TRASH":
            # Suppression définitive de la boîte pour cet utilisateur (RG04/RG05)
            db.delete(boite)
        else:
            # Déplacement vers la corbeille
            boite.dossier = "TRASH"
            boite.date_suppression = datetime.now(timezone.utc)
            db.add(boite)

        db.commit()
        return True

    def bulk_action(
        self, db: Session, user_id: int, ids: List[int], action: BulkActionType
    ) -> None:
        if not ids:
            return

        boxes = db.scalars(
            select(Boite).where(
                Boite.utilisateur_id == user_id, Boite.message_id.in_(ids)
            )
        ).all()

        for b in boxes:
            if action == "read":
                b.lu = True
                b.date_lecture = datetime.now(timezone.utc)
            elif action == "unread":
                b.lu = False
                b.date_lecture = None
            elif action == "archive":
                b.dossier = "ARCHIVE"
            elif action == "trash":
                b.dossier = "TRASH"
                b.date_suppression = datetime.now(timezone.utc)
            elif action == "restore":
                b.dossier = "SENT" if b.type_dest == "FROM" else "INBOX"
                b.date_suppression = None
            elif action == "delete":
                db.delete(b)
                continue
            db.add(b)

        db.commit()

    def create_attachment(
        self,
        db: Session,
        *,
        nom_fichier: str,
        type_mime: str,
        taille: int,
        chemin_stockage: str,
        message_id: Optional[int] = None,
    ) -> PieceJointe:
        pj = PieceJointe(
            nom_fichier=nom_fichier,
            type_mime=type_mime,
            taille=taille,
            chemin_stockage=chemin_stockage,
            message_id=message_id,
        )
        db.add(pj)
        db.commit()
        db.refresh(pj)
        return pj

    def get_attachment(self, db: Session, attachment_id: int) -> Optional[PieceJointe]:
        return db.get(PieceJointe, attachment_id)

    def attach_files_to_message(
        self, db: Session, attachment_ids: List[int], message_id: int
    ) -> None:
        if not attachment_ids:
            return
        attachments = db.scalars(
            select(PieceJointe).where(PieceJointe.id.in_(attachment_ids))
        ).all()
        for a in attachments:
            a.message_id = message_id
            db.add(a)


mail_repository = MailRepository()

