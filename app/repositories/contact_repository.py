from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models.contact import Contact
from app.models.user import Utilisateur


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ContactRepository:
    """Toutes les requêtes sont filtrées par `utilisateur_id` (propriétaire du carnet)."""

    def list_for_user(
        self,
        db: Session,
        *,
        user_id: int,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Contact], int]:
        filters = [Contact.utilisateur_id == user_id, Utilisateur.actif.is_(True)]
        if q and q.strip():
            pattern = f"%{_escape_like(q.strip())}%"
            filters.append(
                or_(
                    Utilisateur.nom.ilike(pattern, escape="\\"),
                    Utilisateur.prenom.ilike(pattern, escape="\\"),
                    Utilisateur.email.ilike(pattern, escape="\\"),
                    Utilisateur.matricule.ilike(pattern, escape="\\"),
                    Utilisateur.fonction.ilike(pattern, escape="\\"),
                )
            )
        join_on = Utilisateur.id == Contact.contact_utilisateur_id

        total = (
            db.scalar(
                select(func.count(Contact.id)).join(Utilisateur, join_on).where(*filters)
            )
            or 0
        )
        stmt = (
            select(Contact)
            .join(Utilisateur, join_on)
            .options(contains_eager(Contact.contact_utilisateur))
            .where(*filters)
            .order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc(), Contact.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all()), total

    def get_for_user(
        self, db: Session, *, user_id: int, contact_id: int
    ) -> Optional[Contact]:
        stmt = select(Contact).where(
            Contact.id == contact_id, Contact.utilisateur_id == user_id
        )
        return db.scalars(stmt).first()

    def get_by_target(
        self, db: Session, *, user_id: int, contact_user_id: int
    ) -> Optional[Contact]:
        stmt = select(Contact).where(
            Contact.utilisateur_id == user_id,
            Contact.contact_utilisateur_id == contact_user_id,
        )
        return db.scalars(stmt).first()

    def create(self, db: Session, *, user_id: int, contact_user_id: int) -> Contact:
        contact = Contact(utilisateur_id=user_id, contact_utilisateur_id=contact_user_id)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    def delete(self, db: Session, *, contact: Contact) -> None:
        db.delete(contact)
        db.commit()


contact_repository = ContactRepository()
