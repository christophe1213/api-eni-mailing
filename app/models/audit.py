from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class Journal(Base):
    __tablename__ = "journal"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    utilisateur_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("utilisateur.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    adresse_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    utilisateur: Mapped[Optional["Utilisateur"]] = relationship("Utilisateur")

    __table_args__ = (
        Index("idx_journal_date", date.desc()),
    )
