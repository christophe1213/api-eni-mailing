from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.models.user import Utilisateur
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[Utilisateur, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(Utilisateur)

    def get_by_email(self, db: Session, *, email: str) -> Optional[Utilisateur]:
        statement = select(Utilisateur).where(Utilisateur.email == email)
        return db.scalars(statement).first()

    def get_by_email_verification(
        self, db: Session, *, email: str
    ) -> Optional[Utilisateur]:
        statement = select(Utilisateur).where(
            Utilisateur.email_verification == email.strip().lower()
        )
        return db.scalars(statement).first()

    def get_by_matricule(self, db: Session, *, matricule: str) -> Optional[Utilisateur]:
        statement = select(Utilisateur).where(Utilisateur.matricule == matricule)
        return db.scalars(statement).first()

    def get_users_filtered(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        role: Optional[str] = None,
        level: Optional[str] = None,
        track: Optional[str] = None,
        active: Optional[bool] = None,
        pending: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Utilisateur], int]:
        query = select(Utilisateur)
        count_query = select(func.count(Utilisateur.id))

        filters = []
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Utilisateur.nom.ilike(pattern),
                    Utilisateur.prenom.ilike(pattern),
                    Utilisateur.email.ilike(pattern),
                    Utilisateur.matricule.ilike(pattern),
                    Utilisateur.fonction.ilike(pattern),
                )
            )
        if role:
            filters.append(Utilisateur.role == role)
        if level:
            filters.append(Utilisateur.niveau_code == level)
        if track:
            filters.append(Utilisateur.parcours_code == track)
        if active is not None:
            filters.append(Utilisateur.actif == active)
        if pending:
            filters.append(Utilisateur.en_attente.is_(True))

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total = db.scalar(count_query) or 0
        items = list(db.scalars(query.order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc()).offset(skip).limit(limit)).all())
        return items, total


user_repository = UserRepository()
