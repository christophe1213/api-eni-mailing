from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.schemas.audit import AdminStats, AuditLogResponse
from app.schemas.base import Page
from app.services.audit_service import audit_service

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def get_admin_stats(
    db: Session = Depends(deps.get_db),
    admin_user: Utilisateur = Depends(deps.get_current_admin),
) -> Any:
    return audit_service.get_stats(db)


@router.get("/logs", response_model=Page[AuditLogResponse])
def get_audit_logs(
    q: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    admin_user: Utilisateur = Depends(deps.get_current_admin),
) -> Any:
    return audit_service.get_logs(
        db, q=q, action=action, page=page, page_size=pageSize
    )

