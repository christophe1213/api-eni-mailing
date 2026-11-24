from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Tuple, Any
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import Session, joinedload
from app.models.audit import Journal
from app.models.user import Utilisateur
from app.models.mail import Message
from app.models.group import ListeDiffusion


class AuditRepository:
    def log(
        self,
        db: Session,
        *,
        user_id: Optional[int] = None,
        action: str,
        details: Optional[Any] = None,
        ip: Optional[str] = None,
    ) -> Journal:
        journal = Journal(
            utilisateur_id=user_id,
            action=action,
            details=details,
            adresse_ip=ip,
        )
        db.add(journal)
        db.commit()
        db.refresh(journal)
        return journal

    def get_logs(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Journal], int]:
        query = (
            select(Journal)
            .options(joinedload(Journal.utilisateur))
        )
        count_query = select(func.count(Journal.id))

        filters = []
        if action:
            filters.append(Journal.action == action)
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Journal.action.ilike(pattern),
                    Journal.adresse_ip.ilike(pattern),
                )
            )

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        total = db.scalar(count_query) or 0
        items = list(
            db.scalars(
                query.order_by(Journal.date.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )
        return items, total

    def get_stats(self, db: Session) -> dict:
        # Utilisateurs
        total_users = db.scalar(select(func.count(Utilisateur.id))) or 0
        active_users = db.scalar(select(func.count(Utilisateur.id)).where(Utilisateur.actif == True)) or 0

        roles_counts = db.execute(
            select(Utilisateur.role, func.count(Utilisateur.id)).group_by(Utilisateur.role)
        ).all()
        by_role = {"ADMIN": 0, "PERSONNEL": 0, "ENSEIGNANT": 0, "ETUDIANT": 0}
        for role, count in roles_counts:
            if role in by_role:
                by_role[role] = count

        # Messages
        total_sent = db.scalar(
            select(func.count(Message.id)).where(Message.date_envoi != None)
        ) or 0

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = db.scalar(
            select(func.count(Message.id)).where(
                Message.date_envoi != None,
                Message.date_creation >= today_start,
            )
        ) or 0

        announcements = db.scalar(
            select(func.count(Message.id)).where(Message.est_annonce == True)
        ) or 0

        total_groups = db.scalar(select(func.count(ListeDiffusion.id))) or 0

        # Activité des 7 derniers jours
        activity = []
        for i in range(6, -1, -1):
            day_dt = (datetime.now(timezone.utc) - timedelta(days=i)).date()
            day_start = datetime.combine(day_dt, datetime.min.time(), tzinfo=timezone.utc)
            day_end = datetime.combine(day_dt, datetime.max.time(), tzinfo=timezone.utc)
            day_count = db.scalar(
                select(func.count(Message.id)).where(
                    Message.date_envoi != None,
                    Message.date_creation >= day_start,
                    Message.date_creation <= day_end,
                )
            ) or 0
            activity.append({"date": day_dt.isoformat(), "count": day_count})

        # Top expéditeurs
        top_senders_rows = db.execute(
            select(Utilisateur, func.count(Message.id).label("cnt"))
            .join(Message, Message.expediteur_id == Utilisateur.id)
            .where(Message.date_envoi != None)
            .group_by(Utilisateur.id)
            .order_by(desc("cnt"))
            .limit(5)
        ).all()

        top_senders = []
        for user, cnt in top_senders_rows:
            top_senders.append({
                "user": user,
                "count": cnt,
            })

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "by_role": by_role,
            },
            "messages_sent": total_sent,
            "messages_today": messages_today,
            "announcements": announcements,
            "groups": total_groups,
            "activity": activity,
            "top_senders": top_senders,
        }


audit_repository = AuditRepository()

