from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.models.template import Modele
from app.schemas.template import TemplatePayload


class TemplateRepository:
    def list_templates(self, db: Session) -> List[Modele]:
        stmt = (
            select(Modele)
            .options(joinedload(Modele.auteur))
            .order_by(Modele.titre.asc())
        )
        return list(db.scalars(stmt).all())

    def get_by_id(self, db: Session, template_id: int) -> Optional[Modele]:
        stmt = (
            select(Modele)
            .where(Modele.id == template_id)
            .options(joinedload(Modele.auteur))
        )
        return db.scalars(stmt).first()

    def create(
        self, db: Session, *, author_id: int, payload: TemplatePayload
    ) -> Modele:
        template = Modele(
            titre=payload.title,
            categorie=payload.category,
            objet=payload.subject,
            corps=payload.body,
            auteur_id=author_id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    def update(
        self, db: Session, *, template: Modele, payload: TemplatePayload
    ) -> Modele:
        template.titre = payload.title
        template.categorie = payload.category
        template.objet = payload.subject
        template.corps = payload.body

        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    def delete(self, db: Session, *, template: Modele) -> None:
        db.delete(template)
        db.commit()


template_repository = TemplateRepository()

