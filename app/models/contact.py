from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import Utilisateur


class Contact(Base):
    """Lien « carnet de contacts » : `utilisateur_id` (le propriétaire du carnet)
    a ajouté `contact_utilisateur_id` (un autre utilisateur de la plateforme).
    Aucune donnée de l'utilisateur n'est dupliquée : nom, e-mail, etc. sont lus
    dans la table `utilisateur`."""

    __tablename__ = "contact"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateur.id", ondelete="CASCADE"), nullable=False
    )

    contact_utilisateur: Mapped["Utilisateur"] = relationship(
        "Utilisateur", foreign_keys=[contact_utilisateur_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "utilisateur_id",
            "contact_utilisateur_id",
            name="uq_contact_utilisateur_contact",
        ),
        CheckConstraint(
            "utilisateur_id <> contact_utilisateur_id",
            name="ck_contact_pas_soi_meme",
        ),
    )
