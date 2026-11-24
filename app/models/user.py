from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    SmallInteger,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    false,
    true,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class Niveau(Base):
    __tablename__ = "niveau"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    ordre: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Parcours(Base):
    __tablename__ = "parcours"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    libelle: Mapped[str] = mapped_column(String(100), nullable=False)


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    matricule: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    prenom: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)  # e-mail ENI
    # E-mail externe de vérification / récupération (validation par OTP)
    email_verification: Mapped[Optional[str]] = mapped_column(
        String(150), unique=True, nullable=True
    )
    email_verification_verifie: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    mot_de_passe: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    niveau_code: Mapped[Optional[str]] = mapped_column(
        String(5), ForeignKey("niveau.code"), nullable=True
    )
    parcours_code: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("parcours.code"), nullable=True
    )
    fonction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notif_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Vérification de l'adresse e-mail par code OTP
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=true(), nullable=False)
    # Inscription en ligne en attente de validation (RG13) — distinct d'un compte désactivé
    en_attente: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    derniere_connexion: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    # Photo de profil : date de dernière mise à jour (NULL = pas de photo).
    # Le fichier est stocké dans AVATAR_DIR/<id>.jpg ; la date sert à versionner l'URL (cache navigateur).
    photo_maj: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    niveau: Mapped[Optional["Niveau"]] = relationship("Niveau")
    parcours: Mapped[Optional["Parcours"]] = relationship("Parcours")

    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN','PERSONNEL','ENSEIGNANT','ETUDIANT')",
            name="ck_utilisateur_role",
        ),
        CheckConstraint(
            "role <> 'ETUDIANT' OR niveau_code IS NOT NULL",
            name="ck_etudiant_niveau",
        ),
        CheckConstraint(
            "email_verification IS NULL OR email_verification <> email",
            name="ck_email_verification_distinct",
        ),
    )

