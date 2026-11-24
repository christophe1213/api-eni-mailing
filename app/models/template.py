from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class Modele(Base):
    __tablename__ = "modele"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titre: Mapped[str] = mapped_column(String(120), nullable=False)
    categorie: Mapped[str] = mapped_column(String(50), nullable=False)
    objet: Mapped[str] = mapped_column(String(255), nullable=False)
    corps: Mapped[str] = mapped_column(Text, nullable=False)
    auteur_id: Mapped[int] = mapped_column(ForeignKey("utilisateur.id"), nullable=False)
    date_maj: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    auteur: Mapped["Utilisateur"] = relationship("Utilisateur")

