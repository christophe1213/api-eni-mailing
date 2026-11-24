from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class ListeDiffusion(Base):
    __tablename__ = "liste_diffusion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    adresse: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    critere_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    critere_niveau: Mapped[Optional[str]] = mapped_column(
        String(5), ForeignKey("niveau.code"), nullable=True
    )
    critere_parcours: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("parcours.code"), nullable=True
    )
    ouverte_etudiants: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proprietaire_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id"), nullable=False
    )
    date_creation: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    proprietaire: Mapped["Utilisateur"] = relationship("Utilisateur")
    membres: Mapped[List["MembreListe"]] = relationship(
        "MembreListe", back_populates="liste", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("type IN ('AUTO','MANUELLE')", name="ck_liste_type"),
    )


class MembreListe(Base):
    __tablename__ = "membre_liste"

    liste_id: Mapped[int] = mapped_column(
        ForeignKey("liste_diffusion.id", ondelete="CASCADE"), primary_key=True
    )
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), primary_key=True
    )
    date_ajout: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    liste: Mapped["ListeDiffusion"] = relationship("ListeDiffusion", back_populates="membres")
    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur")
