from typing import Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.schemas.template import TemplateResponse, TemplatePayload
from app.services.template_service import template_service
from app.services.audit_service import audit_service

router = APIRouter()


@router.get("", response_model=List[TemplateResponse])
def get_templates(
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_personnel_or_admin),
) -> Any:
    return template_service.list_templates(db)


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template_by_id(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_personnel_or_admin),
) -> Any:
    return template_service.get_template(db, template_id=template_id)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplatePayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_personnel_or_admin),
) -> Any:
    template = template_service.create_template(
        db, author=current_user, payload=payload
    )
    audit_service.log(
        db,
        user_id=current_user.id,
        action="TEMPLATE_CREATE",
        details={"templateId": template.id, "title": template.title},
    )
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    payload: TemplatePayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_personnel_or_admin),
) -> Any:
    template = template_service.update_template(
        db, template_id=template_id, payload=payload
    )
    audit_service.log(
        db,
        user_id=current_user.id,
        action="TEMPLATE_UPDATE",
        details={"templateId": template_id, "title": template.title},
    )
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_personnel_or_admin),
) -> None:
    template_service.delete_template(db, template_id=template_id)
    audit_service.log(
        db,
        user_id=current_user.id,
        action="TEMPLATE_DELETE",
        details={"templateId": template_id},
    )
    return None

