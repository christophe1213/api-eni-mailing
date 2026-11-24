from app.repositories.base import BaseRepository
from app.repositories.user_repository import user_repository, UserRepository
from app.repositories.mail_repository import mail_repository, MailRepository
from app.repositories.group_repository import group_repository, GroupRepository
from app.repositories.template_repository import template_repository, TemplateRepository
from app.repositories.audit_repository import audit_repository, AuditRepository

__all__ = [
    "BaseRepository",
    "user_repository",
    "UserRepository",
    "mail_repository",
    "MailRepository",
    "group_repository",
    "GroupRepository",
    "template_repository",
    "TemplateRepository",
    "audit_repository",
    "AuditRepository",
]
