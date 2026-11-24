from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    BigInteger,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expediteur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id"), nullable=False
    )
    objet: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    corps: Mapped[str] = mapped_column(Text, default="", nullable=False)
    priorite: Mapped[str] = mapped_column(String(10), default="NORMALE", nullable=False)
    est_annonce: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("message.id", ondelete="SET NULL"), nullable=True
    )
    date_creation: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    date_envoi: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    expediteur: Mapped["Utilisateur"] = relationship("Utilisateur")
    parent: Mapped[Optional["Message"]] = relationship("Message", remote_side=[id])
    pieces_jointes: Mapped[List["PieceJointe"]] = relationship(
        "PieceJointe", back_populates="message", cascade="all, delete-orphan"
    )
    boites: Mapped[List["Boite"]] = relationship(
        "Boite", back_populates="message", cascade="all, delete-orphan"
    )
    groupes_cibles: Mapped[List["MessageListe"]] = relationship(
        "MessageListe", back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("priorite IN ('NORMALE','HAUTE')", name="ck_message_priorite"),
    )


class MessageListe(Base):
    __tablename__ = "message_liste"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("message.id", ondelete="CASCADE"), primary_key=True
    )
    liste_id: Mapped[int] = mapped_column(
        ForeignKey("liste_diffusion.id"), primary_key=True
    )
    type_dest: Mapped[str] = mapped_column(String(5), nullable=False)

    message: Mapped["Message"] = relationship("Message", back_populates="groupes_cibles")
    liste: Mapped["ListeDiffusion"] = relationship("ListeDiffusion")

    __table_args__ = (
        CheckConstraint("type_dest IN ('TO','CC','BCC')", name="ck_msglist_typedest"),
    )


class Boite(Base):
    __tablename__ = "boite"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("message.id", ondelete="CASCADE"), nullable=False
    )
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id"), nullable=False
    )
    type_dest: Mapped[str] = mapped_column(String(5), nullable=False)
    dossier: Mapped[str] = mapped_column(String(15), nullable=False)
    lu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favori: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_lecture: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    date_suppression: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    message: Mapped["Message"] = relationship("Message", back_populates="boites")
    utilisateur: Mapped["Utilisateur"] = relationship("Utilisateur")

    __table_args__ = (
        CheckConstraint("type_dest IN ('FROM','TO','CC','BCC')", name="ck_boite_typedest"),
        CheckConstraint(
            "dossier IN ('INBOX','SENT','DRAFTS','ARCHIVE','TRASH')",
            name="ck_boite_dossier",
        ),
        UniqueConstraint("message_id", "utilisateur_id", "type_dest", name="uq_boite_dest"),
        Index("idx_boite_user_dossier", "utilisateur_id", "dossier", "lu"),
    )


class PieceJointe(Base):
    __tablename__ = "piece_jointe"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("message.id", ondelete="CASCADE"), nullable=True
    )
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    type_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    taille: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(String(500), nullable=False)

    message: Mapped[Optional["Message"]] = relationship(
        "Message", back_populates="pieces_jointes"
    )

    __table_args__ = (
        CheckConstraint("taille <= 10485760", name="ck_piece_taille_max"),
    )
