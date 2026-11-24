from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.group import ListeDiffusion
from app.models.user import Utilisateur
from app.repositories.group_repository import group_repository
from app.schemas.group import GroupPayload, GroupResponse
from app.schemas.user import UserSummary
from app.services.avatar_service import avatar_url


def group_to_response(
    db: Session, group: ListeDiffusion, include_members: bool = False
) -> GroupResponse:
    owner_summary = UserSummary(
        id=group.proprietaire.id,
        first_name=group.proprietaire.prenom,
        last_name=group.proprietaire.nom,
        email=group.proprietaire.email,
        role=group.proprietaire.role,  # type: ignore
        avatar_url=avatar_url(group.proprietaire),
    )
    count = group_repository.count_members(db, group)

    members_summary: Optional[List[UserSummary]] = None
    if include_members:
        resolved_users = group_repository.resolve_members(db, group)
        members_summary = [
            UserSummary(
                id=u.id,
                first_name=u.prenom,
                last_name=u.nom,
                email=u.email,
                role=u.role,  # type: ignore
                avatar_url=avatar_url(u),
            )
            for u in resolved_users
        ]

    return GroupResponse(
        id=group.id,
        name=group.nom,
        address=group.adresse,
        description=group.description or "",
        type=group.type,  # type: ignore
        criteria_role=group.critere_role,  # type: ignore
        criteria_level=group.critere_niveau,  # type: ignore
        criteria_track=group.critere_parcours,  # type: ignore
        open_to_students=group.ouverte_etudiants,
        owner=owner_summary,
        member_count=count,
        created_at=group.date_creation,
        members=members_summary,
    )


class GroupService:
    def list_groups(self, db: Session, q: Optional[str] = None) -> List[GroupResponse]:
        groups = group_repository.list_groups(db, q=q)
        return [group_to_response(db, g, include_members=False) for g in groups]

    def get_group(self, db: Session, group_id: int) -> GroupResponse:
        group = group_repository.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liste de diffusion non trouvée.",
            )
        return group_to_response(db, group, include_members=True)

    def create_group(
        self, db: Session, *, owner: Utilisateur, payload: GroupPayload
    ) -> GroupResponse:
        if group_repository.get_by_name(db, payload.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Une liste avec ce nom existe déjà.",
            )
        if group_repository.get_by_address(db, payload.address):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Une liste avec cette adresse existe déjà.",
            )

        group = group_repository.create(db, owner_id=owner.id, payload=payload)
        return group_to_response(db, group, include_members=True)

    def update_group(
        self,
        db: Session,
        *,
        group_id: int,
        current_user: Utilisateur,
        payload: GroupPayload,
    ) -> GroupResponse:
        group = group_repository.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liste de diffusion non trouvée.",
            )

        if current_user.role != "ADMIN" and group.proprietaire_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à modifier cette liste.",
            )

        updated = group_repository.update(db, group=group, payload=payload)
        return group_to_response(db, updated, include_members=True)

    def delete_group(
        self, db: Session, *, group_id: int, current_user: Utilisateur
    ) -> None:
        group = group_repository.get_by_id(db, group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liste de diffusion non trouvée.",
            )

        if current_user.role != "ADMIN" and group.proprietaire_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à supprimer cette liste.",
            )

        group_repository.delete(db, group=group)


group_service = GroupService()

