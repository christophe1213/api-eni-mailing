import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.repositories.audit_repository import audit_repository
from app.schemas.audit import AuditLogResponse, AdminStats, UserStats, ActivityStat, TopSenderStat
from app.schemas.base import Page
from app.schemas.user import UserSummary
from app.services.avatar_service import avatar_url


class AuditService:
    def log(
        self,
        db: Session,
        *,
        user_id: Optional[int] = None,
        action: str,
        details: Optional[Any] = None,
        ip: Optional[str] = None,
    ) -> None:
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else (str(details) if details else "")
        audit_repository.log(
            db,
            user_id=user_id,
            action=action,
            details=details_str,
            ip=ip,
        )

    def get_logs(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        action: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[AuditLogResponse]:
        skip = (page - 1) * page_size
        logs, total = audit_repository.get_logs(
            db, q=q, action=action, skip=skip, limit=page_size
        )

        items = []
        for log in logs:
            user_summary = None
            if log.utilisateur:
                user_summary = UserSummary(
                    id=log.utilisateur.id,
                    first_name=log.utilisateur.prenom,
                    last_name=log.utilisateur.nom,
                    email=log.utilisateur.email,
                    role=log.utilisateur.role,  # type: ignore
                    avatar_url=avatar_url(log.utilisateur),
                )
            items.append(
                AuditLogResponse(
                    id=log.id,
                    user=user_summary,
                    action=log.action,
                    details=str(log.details) if log.details else "",
                    ip=log.adresse_ip,
                    date=log.date,
                )
            )

        return Page[AuditLogResponse](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_stats(self, db: Session) -> AdminStats:
        raw_stats = audit_repository.get_stats(db)

        top_senders = []
        for s in raw_stats["top_senders"]:
            u = s["user"]
            top_senders.append(
                TopSenderStat(
                    user=UserSummary(
                        id=u.id,
                        first_name=u.prenom,
                        last_name=u.nom,
                        email=u.email,
                        role=u.role,
                        avatar_url=avatar_url(u),
                    ),
                    count=s["count"],
                )
            )

        return AdminStats(
            users=UserStats(
                total=raw_stats["users"]["total"],
                active=raw_stats["users"]["active"],
                by_role=raw_stats["users"]["by_role"],
            ),
            messages_sent=raw_stats["messages_sent"],
            messages_today=raw_stats["messages_today"],
            announcements=raw_stats["announcements"],
            groups=raw_stats["groups"],
            activity=[ActivityStat(**a) for a in raw_stats["activity"]],
            top_senders=top_senders,
        )


audit_service = AuditService()

