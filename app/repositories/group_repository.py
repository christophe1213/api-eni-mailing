from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload
from app.models.group import ListeDiffusion, MembreListe
from app.models.user import Utilisateur
from app.schemas.group import GroupPayload


class GroupRepository:
    def list_groups(self, db: Session, q: Optional[str] = None) -> List[ListeDiffusion]:
        stmt = (
            select(ListeDiffusion)
            .options(
                joinedload(ListeDiffusion.proprietaire),
                joinedload(ListeDiffusion.membres).joinedload(MembreListe.utilisateur),
            )
        )
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    ListeDiffusion.nom.ilike(pattern),
                    ListeDiffusion.adresse.ilike(pattern),
                    ListeDiffusion.description.ilike(pattern),
                )
            )
        return list(db.scalars(stmt.order_by(ListeDiffusion.nom.asc())).unique().all())

    def get_by_id(self, db: Session, group_id: int) -> Optional[ListeDiffusion]:
        stmt = (
            select(ListeDiffusion)
            .where(ListeDiffusion.id == group_id)
            .options(
                joinedload(ListeDiffusion.proprietaire),
                joinedload(ListeDiffusion.membres).joinedload(MembreListe.utilisateur),
            )
        )
        return db.scalars(stmt).first()

    def get_by_name(self, db: Session, name: str) -> Optional[ListeDiffusion]:
        stmt = select(ListeDiffusion).where(ListeDiffusion.nom == name)
        return db.scalars(stmt).first()

    def get_by_address(self, db: Session, address: str) -> Optional[ListeDiffusion]:
        stmt = select(ListeDiffusion).where(ListeDiffusion.adresse == address)
        return db.scalars(stmt).first()

    def resolve_members(self, db: Session, group: ListeDiffusion) -> List[Utilisateur]:
        if group.type == "AUTO":
            filters = [Utilisateur.actif == True]
            if group.critere_role:
                filters.append(Utilisateur.role == group.critere_role)
            if group.critere_niveau:
                filters.append(Utilisateur.niveau_code == group.critere_niveau)
            if group.critere_parcours:
                filters.append(Utilisateur.parcours_code == group.critere_parcours)

            stmt = select(Utilisateur).where(*filters).order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc())
            return list(db.scalars(stmt).all())
        else:
            # MANUELLE
            stmt = (
                select(Utilisateur)
                .join(MembreListe, MembreListe.utilisateur_id == Utilisateur.id)
                .where(MembreListe.liste_id == group.id, Utilisateur.actif == True)
                .order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc())
            )
            return list(db.scalars(stmt).all())

    def count_members(self, db: Session, group: ListeDiffusion) -> int:
        if group.type == "AUTO":
            filters = [Utilisateur.actif == True]
            if group.critere_role:
                filters.append(Utilisateur.role == group.critere_role)
            if group.critere_niveau:
                filters.append(Utilisateur.niveau_code == group.critere_niveau)
            if group.critere_parcours:
                filters.append(Utilisateur.parcours_code == group.critere_parcours)

            count = db.scalar(select(func.count(Utilisateur.id)).where(*filters))
            return count or 0
        else:
            count = db.scalar(
                select(func.count(MembreListe.utilisateur_id)).where(
                    MembreListe.liste_id == group.id
                )
            )
            return count or 0

    def create(
        self, db: Session, *, owner_id: int, payload: GroupPayload
    ) -> ListeDiffusion:
        group = ListeDiffusion(
            nom=payload.name,
            adresse=payload.address,
            description=payload.description or "",
            type=payload.type,
            critere_role=payload.criteria_role,
            critere_niveau=payload.criteria_level,
            critere_parcours=payload.criteria_track,
            ouverte_etudiants=payload.open_to_students,
            proprietaire_id=owner_id,
        )
        db.add(group)
        db.flush()

        if payload.type == "MANUELLE" and payload.member_ids:
            for uid in payload.member_ids:
                membre = MembreListe(liste_id=group.id, utilisateur_id=uid)
                db.add(membre)

        db.commit()
        db.refresh(group)
        return group

    def update(
        self, db: Session, *, group: ListeDiffusion, payload: GroupPayload
    ) -> ListeDiffusion:
        group.nom = payload.name
        group.adresse = payload.address
        group.description = payload.description or ""
        group.type = payload.type
        group.critere_role = payload.criteria_role
        group.critere_niveau = payload.criteria_level
        group.critere_parcours = payload.criteria_track
        group.ouverte_etudiants = payload.open_to_students

        if payload.type == "MANUELLE":
            # Synchroniser les membres
            db.query(MembreListe).filter(MembreListe.liste_id == group.id).delete()
            for uid in payload.member_ids:
                db.add(MembreListe(liste_id=group.id, utilisateur_id=uid))

        db.add(group)
        db.commit()
        db.refresh(group)
        return group

    def delete(self, db: Session, *, group: ListeDiffusion) -> None:
        db.delete(group)
        db.commit()


group_repository = GroupRepository()

