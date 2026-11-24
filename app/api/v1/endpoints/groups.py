from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.schemas.group import GroupResponse, GroupPayload
from app.services.group_service import group_service
from app.services.audit_service import audit_service

router = APIRouter()


@router.get("", response_model=List[GroupResponse])
def get_groups(
    q: Optional[str] = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return group_service.list_groups(db, q=q)


@router.get("/{group_id}", response_model=GroupResponse)
def get_group_by_id(
    group_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return group_service.get_group(db, group_id=group_id)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupPayload,
    db: Session = Depends(deps.get_db),
    teacher_user: Utilisateur = Depends(deps.get_current_teacher_or_above),
) -> Any:
    group = group_service.create_group(db, owner=teacher_user, payload=payload)
    audit_service.log(
        db,
        user_id=teacher_user.id,
        action="GROUP_CREATE",
        details={"groupId": group.id, "groupName": group.name},
    )
    return group


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    payload: GroupPayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    group = group_service.update_group(
        db, group_id=group_id, current_user=current_user, payload=payload
    )
    audit_service.log(
        db,
        user_id=current_user.id,
        action="GROUP_UPDATE",
        details={"groupId": group_id, "groupName": group.name},
    )
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> None:
    group_service.delete_group(db, group_id=group_id, current_user=current_user)
    audit_service.log(
        db,
        user_id=current_user.id,
        action="GROUP_DELETE",
        details={"groupId": group_id},
    )
    return None

