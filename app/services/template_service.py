from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.template import Modele
from app.models.user import Utilisateur
from app.repositories.template_repository import template_repository
from app.schemas.template import TemplatePayload, TemplateResponse
from app.schemas.user import UserSummary
from app.services.avatar_service import avatar_url


def template_to_response(template: Modele) -> TemplateResponse:
    author_summary = UserSummary(
        id=template.auteur.id,
        first_name=template.auteur.prenom,
        last_name=template.auteur.nom,
        email=template.auteur.email,
        role=template.auteur.role,  # type: ignore
        avatar_url=avatar_url(template.auteur),
    )
    return TemplateResponse(
        id=template.id,
        title=template.titre,
        category=template.categorie,
        subject=template.objet,
        body=template.corps,
        author=author_summary,
        updated_at=template.date_maj,
    )


class TemplateService:
    def list_templates(self, db: Session) -> List[TemplateResponse]:
        templates = template_repository.list_templates(db)
        return [template_to_response(t) for t in templates]

    def get_template(self, db: Session, template_id: int) -> TemplateResponse:
        template = template_repository.get_by_id(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle non trouvé.",
            )
        return template_to_response(template)

    def create_template(
        self, db: Session, *, author: Utilisateur, payload: TemplatePayload
    ) -> TemplateResponse:
        created = template_repository.create(db, author_id=author.id, payload=payload)
        return template_to_response(created)

    def update_template(
        self, db: Session, *, template_id: int, payload: TemplatePayload
    ) -> TemplateResponse:
        template = template_repository.get_by_id(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle non trouvé.",
            )
        updated = template_repository.update(db, template=template, payload=payload)
        return template_to_response(updated)

    def delete_template(self, db: Session, *, template_id: int) -> None:
        template = template_repository.get_by_id(db, template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle non trouvé.",
            )
        template_repository.delete(db, template=template)


template_service = TemplateService()

